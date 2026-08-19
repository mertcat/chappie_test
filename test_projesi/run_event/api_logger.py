"""Test adimlarini run event olarak API'ye gonderir, kosum ozetini dosyaya yazar.

Iki isi var:

1. Her adimi API'ye event olarak gonderir (PUBLIC_BASE_URL tanimliysa)
2. Kosum sonunda ozeti config/step_count.json dosyasina yazar

API adresi tanimli DEGILSE kirilmaz: event gonderimi atlanir, adim sayaci ve
ozet yazimi calismaya devam eder. Yani robotu/cihazi olan ama API'si olmayan
bir tezgahta da sorunsuz koser.

ORTAM DEGISKENLERI (hepsi opsiyonel)

    PUBLIC_BASE_URL         API adresi; yoksa event gonderimi atlanir
    RUN_ID                  kosum kimligi (varsayilan: "default_run")
    AGENT_ID                agent kimligi (varsayilan: "local_agent")
    RUNNER_SHARED_SECRET    API kimlik dogrulama basligi

KULLANIM

    from run_event.api_logger import get_api_logger

    kayit = get_api_logger()
    kayit.log_step_passed("3500 TL'lik kalem sepete eklendi.")
    kayit.save_step_count_to_config()      # kosum sonunda
"""
import json
import logging
import os
import subprocess
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

# Ozet dosyasi PROJE KOKUNE gore yaziliyor, calisma dizinine gore DEGIL:
# `pytest` hangi dizinden calistirilirsa calistirilsin ozet hep ayni yere dussun.
_PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIZINI = os.path.join(_PROJE_KOKU, "config")
OZET_DOSYASI = os.path.join(CONFIG_DIZINI, "step_count.json")


class APILogger:
    """Adim sayaci + event gonderimi. Kosum basina TEK ornek kullanilmali."""

    def __init__(self, run_id=None, agent_id=None):
        self.run_id = run_id or os.getenv("RUN_ID", "default_run")
        self.agent_id = agent_id or os.getenv("AGENT_ID", "local_agent")

        temel_adres = os.getenv("PUBLIC_BASE_URL")
        self.base_url = f"{temel_adres}/api/v1" if temel_adres else None

        basliklar = {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true",
            "x-runner-shared-secret": os.getenv("RUNNER_SHARED_SECRET"),
        }
        self.headers = {a: d for a, d in basliklar.items() if d is not None}

        self.seq = 0
        self.step = 0
        self.baslangic = datetime.now()
        self.baslangic_batarya = self._batarya_seviyesi()
        self.bitis_batarya = None

    @staticmethod
    def _batarya_seviyesi():
        """Bagli cihazin batarya yuzdesi. adb yoksa None doner, kirilmaz."""
        try:
            cikti = subprocess.check_output(
                ["adb", "shell", "dumpsys", "battery"],
                stderr=subprocess.STDOUT, text=True, timeout=10,
            )
            for satir in cikti.splitlines():
                satir = satir.strip()
                if satir.startswith("level:"):
                    return int(satir.split(":", 1)[1].strip())
        except Exception:
            return None
        return None

    def send_event(self, event_type: str, detail: str) -> bool:
        """Event gonderir. Adim sayaci API'den BAGIMSIZ olarak her cagrida artar."""
        self.step += 1
        self.seq += 1

        if not detail.startswith("[Adım"):
            detail = f"[Adım {self.step}] {detail}" if detail else detail

        if not self.base_url:
            logger.debug("PUBLIC_BASE_URL tanımlı değil, event atlandı: %s | %s",
                         event_type, detail)
            return False

        gonderi = {
            "ok": True,
            "runEvent": {
                "runId": self.run_id,
                "agentId": self.agent_id,
                "type": event_type,
                "payload": {"detail": detail},
                "is": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "seq": self.seq,
            },
        }
        try:
            yanit = requests.post(
                f"{self.base_url}/agents/runs/{self.run_id}/event",
                json=gonderi, headers=self.headers, timeout=10,
            )
            yanit.raise_for_status()
            return True
        except requests.exceptions.RequestException as hata:
            # Raporlama testi DUSURMEZ: API erisilemiyorsa uyarilir, kosum devam eder.
            logger.warning("Event gönderilemedi (%s): %s", event_type, hata)
            return False

    def log_test_app_launched(self, uygulama: str) -> bool:
        return self.send_event("test_app_launched", f"{uygulama} test app has started")

    def log_step_passed(self, aciklama: str) -> bool:
        return self.send_event("step_passed", aciklama)

    def log_message(self, mesaj: str) -> bool:
        return self.send_event("log", mesaj)

    def log_screenshot_saved(self, yol: str) -> bool:
        return self.send_event("screenshot_saved", f"Screenshot saved: {yol}")

    def save_step_count_to_config(self) -> bool:
        """Kosum ozetini config/step_count.json dosyasina yazar."""
        try:
            os.makedirs(CONFIG_DIZINI, exist_ok=True)
            self.bitis_batarya = self._batarya_seviyesi()

            bitis = datetime.now()
            saniye = (bitis - self.baslangic).total_seconds()

            ozet = {
                "total_steps": self.step,
                "start_time": self.baslangic.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": bitis.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": f"{int(saniye // 60)}m {int(saniye % 60)}s",
                "start_battery_level": self.baslangic_batarya,
                "end_battery_level": self.bitis_batarya,
                "run_id": self.run_id,
                "agent_id": self.agent_id,
            }
            with open(OZET_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(ozet, f, indent=4, ensure_ascii=False)

            logger.info("Koşum özeti yazıldı: %s (%d adım, %s)",
                        OZET_DOSYASI, ozet["total_steps"], ozet["duration"])
            return True
        except Exception as hata:
            logger.error("Koşum özeti yazılamadı: %s", hata)
            return False


_ornek = None


def get_api_logger(run_id=None, agent_id=None) -> APILogger:
    """Kosum boyunca TEK APILogger ornegi.

    Adim sayaci ornek basina tutuldugundan her yeni ornek sayaci sifirlar --
    bu yuzden dogrudan APILogger() yerine bu fonksiyon kullanilmali.
    """
    global _ornek
    if _ornek is None:
        _ornek = APILogger(run_id, agent_id)
    return _ornek
