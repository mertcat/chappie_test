"""'Cihazınız ısındı' uyarisi -- APPIUM BU UYARIYI GOREMEZ, adb ile kapatilir.

NEDEN AYRI BIR DOSYA / NEDEN adb:

Uyari bir Activity ya da dialog DEGIL; launcher'in ciztigi bir SYSTEM_ALERT_WINDOW
overlay'i (cihazda dogrulandi):

    Window #4 Window{... u0 com.token.v1.os.launcher}:
      package=com.token.v1.os.launcher appop=SYSTEM_ALERT_WINDOW
      mFrame=[0,0][720,1280]  mHasSurface=true

Bu pencere uiautomator hiyerarsisine HIC girmiyor: `uiautomator dump` ciktisinda
yalnizca alttaki uygulama (com.tokeninc.ecr) gorunuyor. Yani Appium ile locator
aramak -- metin, resource-id, ne olursa olsun -- BASTAN IMKANSIZ. Ustelik overlay
tam ekran ve tiklanabilir oldugundan altindaki ekrana giden her dokunusu yutuyor;
test "buton tiklandi" sanip beklemeye devam eder ve alakasiz bir adimda duser.

COZUM: pencerenin varligi `dumpsys window` ile anlasilir, Tamam butonuna
`input tap` ile KOORDINATTAN basilir.

KOORDINAT NEREDEN GELIYOR (tahmin degil, APK'dan olculdu):

    com.token.v1.os.launcher, layout/dialog_battery_temparature
      dis kap  : LinearLayout, layout_gravity=bottom, yukseklik 545dp
      son cocuk: TextView id/btn_ok, 320dp x 40dp, layout_gravity=center_horizontal
      metin    : string/alert_button_ok -> tr "Tamam" / en "OK"

Butonun merkezi ekranin ALT KENARINDAN 44dp yukarida, yatayda ortada. 720x1280 /
320dpi cihazda (360, 1192) -- elle denendi, uyari kapandi. Baska cozunurlukte de
dogru olsun diye asagida ekran boyutu ve yogunlugu cihazdan OKUNUYOR.
"""
import logging
import os
import re
import subprocess

logger = logging.getLogger(__name__)

PAKET = "com.token.v1.os.launcher"
BUTON_ALT_MESAFE_DP = 44        # btn_ok merkezinin ekran alt kenarina uzakligi

_olculer = None                 # (genislik, yukseklik, yogunluk) -- bir kez okunur

__all__ = ["ekranda_mi", "kapat_varsa"]


def _adb(*argumanlar, timeout=10) -> str:
    """UDID verilmisse o cihaza konusur (appium_driver ile ayni degisken)."""
    komut = ["adb"]
    udid = os.getenv("UDID")
    if udid:
        komut += ["-s", udid]
    return subprocess.run(komut + list(argumanlar), capture_output=True, text=True,
                          timeout=timeout).stdout


def _ekran_olculeri():
    global _olculer
    if _olculer is None:
        boyut = re.search(r"(\d+)x(\d+)", _adb("shell", "wm", "size"))
        yogunluk = re.search(r"(\d+)", _adb("shell", "wm", "density"))
        _olculer = (int(boyut.group(1)), int(boyut.group(2)),
                    int(yogunluk.group(1)) / 160.0)
    return _olculer


def ekranda_mi() -> bool:
    """Isinma overlay'i su an ciziliyor mu."""
    cikti = _adb("shell", "dumpsys", "window", "windows")
    # Launcher'in overlay penceresi: SYSTEM_ALERT_WINDOW izniyle acilmis ve
    # yuzeyi olan. Launcher'in NORMAL activity penceresi de ayni pakete ait
    # oldugundan appop satiri sart.
    for blok in cikti.split("Window #"):
        if PAKET in blok and "SYSTEM_ALERT_WINDOW" in blok and "mHasSurface=true" in blok:
            return True
    return False


def kapat_varsa() -> bool:
    """Uyari ekrandaysa Tamam'a basar. Basildiysa True doner.

    TESTI DUSURMEZ: kapanmasa bile yalnizca gunluge yazar, cagiran akisina devam
    eder -- uzun kosumda uyari birkac kez cikabilir, her seferinde kapatilir.
    """
    if not ekranda_mi():
        return False

    genislik, yukseklik, yogunluk = _ekran_olculeri()
    x = genislik // 2
    y = yukseklik - int(BUTON_ALT_MESAFE_DP * yogunluk)
    logger.warning("'Cihazınız ısındı' uyarısı çıktı -- Tamam'a basılıyor (%d, %d).",
                   x, y)
    _adb("shell", "input", "tap", str(x), str(y))

    if ekranda_mi():
        logger.warning("Uyarı ilk dokunuşta kapanmadı, tekrar deneniyor.")
        _adb("shell", "input", "tap", str(x), str(y))
    return True


if __name__ == "__main__":
    # Teshis: python tests/cihaz_uyarisi.py
    print("uyarı ekranda mı:", ekranda_mi())
    print("kapatıldı mı    :", kapat_varsa())
