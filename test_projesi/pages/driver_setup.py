"""Appium surucusunu kurar.

Cihaz bilgisi ortam degiskenlerinden gelir; yoksa `adb devices` ciktisindaki
tek cihaz kullanilir. Boylece tek cihazli tezgahta hicbir ayar gerekmez.
"""
import logging
import os
import subprocess

from appium import webdriver
from appium.options.android import UiAutomator2Options

logger = logging.getLogger(__name__)

APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")


def takili_cihazi_bul() -> str:
    """`adb devices` ciktisindaki tek cihazin UDID'sini dondurur."""
    cikti = subprocess.run(["adb", "devices"], capture_output=True, text=True,
                           timeout=10).stdout
    cihazlar = [s.split("\t")[0] for s in cikti.splitlines()[1:]
                if s.strip().endswith("device")]
    if not cihazlar:
        raise Exception("HATA: adb'de takılı cihaz yok. Kabloyu ve `adb devices`i kontrol edin.")
    if len(cihazlar) > 1:
        raise Exception(
            f"HATA: birden fazla cihaz takılı ({', '.join(cihazlar)}). "
            "UDID ortam değişkeniyle hangisi olduğunu belirtin."
        )
    return cihazlar[0]


def surucu_olustur():
    udid = os.getenv("UDID") or takili_cihazi_bul()
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
    return webdriver.Remote(APPIUM_URL, options=UiAutomator2Options().load_capabilities(caps))
