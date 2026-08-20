"""Appium oturumunun kuruldugu TEK dosya.

``tests/chappie_entegrasyon.py`` ile ayni desen: orada robot baglanir, burada cihaz.
Ikisi de duz fonksiyon -- pytest fixture'i DEGIL, o yuzden ``conftest.py`` gerekmez:

    driver = appium_driver.baslat()
    ...
    appium_driver.kapat(driver)

Iki isi var:

1. Cihazi bulup Appium oturumunu acar (``baslat()``)
2. SOGUK BASLATMA: testin bilinen bir noktadan basladigini garanti eder

CIHAZ SECIMI: ``UDID`` ortam degiskeni verilmisse o kullanilir, verilmemisse
``adb devices`` ciktisindaki tek cihaz alinir. Tek cihazli tezgahta hicbir ayar
gerekmez; birden fazla cihaz takiliysa hangisi oldugu ACIKCA sorulur -- yanlis
cihazda kart okutmak sessizce olmamali.

ORTAM DEGISKENLERI

    UDID          hangi cihaz (verilmezse adb'deki tek cihaz)
    APPIUM_URL    Appium sunucusu (varsayilan http://127.0.0.1:4723)
"""
import logging
import os
import subprocess

from appium import webdriver
from appium.options.android import UiAutomator2Options

from run_event.api_logger import get_api_logger

logger = logging.getLogger(__name__)

APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")

ANA_UYGULAMA = "com.token.v1.os.launcher"
# Kosum sirasinda one cikabilen diger paketler; soguk baslatmada kapatiliyorlar.
YAN_PAKETLER = ("com.tokeninc.ecr", "com.tokeninc.sardis.paymentgateway",
                "com.tokeninc.fiscalservice")

__all__ = ["baslat", "kapat"]


def takili_cihazi_bul() -> str:
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


def soguk_baslat(surucu):
    """Testin BILINEN bir noktadan basladigini garanti eder.

    ``noReset=True`` oldugundan cihaz onceki kosumdan kalma bir ekranda (yarim
    kalmis odeme, acik bir dialog) durabilir; oradan devam etmek testi ilk
    adimda dusururdu. Ilgili paketleri kapatip ana uygulamayi one aliyoruz.
    """
    for paket in YAN_PAKETLER:
        try:
            surucu.terminate_app(paket)
        except Exception:
            pass          # paket zaten kapaliysa sorun degil
    surucu.activate_app(ANA_UYGULAMA)
    logger.info("Soğuk başlatma yapıldı, ana menü açık.")


def baslat():
    """Appium oturumu acar, cihazi bilinen bir noktaya getirir, surucuyu dondurur."""
    udid = os.getenv("UDID") or takili_cihazi_bul()
    logger.info("Appium oturumu açılıyor (cihaz: %s).", udid)

    caps = dict(
        platformName="Android",
        automationName="uiautomator2",
        udid=udid,
        appPackage=ANA_UYGULAMA,
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

    soguk_baslat(surucu)
    get_api_logger().log_test_app_launched(ANA_UYGULAMA)
    return surucu


def kapat(surucu):
    """Kosum ozetini yazar, oturumu kapatir. Kapanis yolunda oldugu icin hata yutar."""
    # Kosum ozeti: kac adim, ne kadar surdu, batarya ne kadar dustu.
    get_api_logger().save_step_count_to_config()
    try:
        surucu.quit()
    except Exception as hata:
        logger.warning("Appium oturumu kapatılamadı: %s", hata)
