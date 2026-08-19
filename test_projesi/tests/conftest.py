"""Ortak fixture'lar: Appium oturumu ve chappie."""
import logging
import os
import subprocess

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options

# Chappie'nin bu projeye baglandigi TEK dosya. Bu satir olmadan `chappie`
# fixture'i testlerden gorunmez.
#
# pytest.ini icinde `-p tests.chappie_entegrasyon` ile eklenti olarak YUKLEMEYIN:
# -p eklentileri conftest toplanmasindan ONCE yuklenir, o anda proje koku
# sys.path'te olmadigindan `pytest` konsol betigiyle "No module named 'tests'"
# hatasi verir.
from run_event.api_logger import get_api_logger
from tests.chappie_entegrasyon import chappie  # noqa: F401

logger = logging.getLogger(__name__)

APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")

ANA_UYGULAMA = "com.token.v1.os.launcher"
# Kosum sirasinda one cikabilen diger paketler; soguk baslatmada kapatiliyorlar.
YAN_PAKETLER = ("com.tokeninc.ecr", "com.tokeninc.sardis.paymentgateway",
                "com.tokeninc.fiscalservice")


def _takili_cihazi_bul() -> str:
    """`adb devices` ciktisindaki tek cihazin UDID'sini dondurur."""
    cikti = subprocess.run(["adb", "devices"], capture_output=True, text=True,
                           timeout=10).stdout
    cihazlar = [s.split("\t")[0] for s in cikti.splitlines()[1:]
                if s.strip().endswith("device")]
    if not cihazlar:
        raise Exception("HATA: adb'de takılı cihaz yok. `adb devices` çıktısını kontrol edin.")
    if len(cihazlar) > 1:
        raise Exception(
            f"HATA: birden fazla cihaz takılı ({', '.join(cihazlar)}). "
            "Hangisi olduğunu UDID ortam değişkeniyle belirtin."
        )
    return cihazlar[0]


@pytest.fixture(scope="session")
def driver():
    """Kosum boyunca TEK Appium oturumu."""
    udid = os.getenv("UDID") or _takili_cihazi_bul()
    logger.info("Appium oturumu açılıyor (cihaz: %s).", udid)

    caps = dict(
        platformName="Android",
        automationName="uiautomator2",
        udid=udid,
        appPackage="com.token.v1.os.launcher",
        appActivity="com.token.v1.os.launcher.menu.MainMenuActivity",
        noReset=True,
        autoGrantPermissions=True,
        newCommandTimeout=300,
        skipUnlock=True,
        skipServerInstallation=True,
        enforceAppInstall=False,
        systemFontsPath="",
    )
    surucu = webdriver.Remote(APPIUM_URL,
                              options=UiAutomator2Options().load_capabilities(caps))

    # SOGUK BASLATMA -- testin BILINEN bir noktadan basladigini garanti eder.
    # noReset=True oldugundan cihaz onceki kosumdan kalma bir ekranda (yarim
    # kalmis odeme, acik bir dialog) durabilir; oradan devam etmek testi ilk
    # adimda dusururdu. Ilgili paketleri kapatip ana uygulamayi one aliyoruz.
    for paket in YAN_PAKETLER:
        try:
            surucu.terminate_app(paket)
        except Exception:
            pass          # paket zaten kapaliysa sorun degil
    surucu.activate_app(ANA_UYGULAMA)
    logger.info("Soğuk başlatma yapıldı, ana menü açık.")
    get_api_logger().log_test_app_launched(ANA_UYGULAMA)

    yield surucu

    # Kosum ozeti: kac adim, ne kadar surdu, batarya ne kadar dustu.
    get_api_logger().save_step_count_to_config()

    try:
        surucu.quit()
    except Exception:
        pass
