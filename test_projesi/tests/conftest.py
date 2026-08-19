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
from tests.chappie_entegrasyon import chappie  # noqa: F401

logger = logging.getLogger(__name__)

APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")


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

    yield surucu

    try:
        surucu.quit()
    except Exception:
        pass
