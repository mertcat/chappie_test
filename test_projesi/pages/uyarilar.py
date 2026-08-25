"""Kosum sirasinda HERHANGI BIR ANDA cikabilen cihaz uyarilarinin locator'lari.

Bunlar bir ekrana degil, CIHAZA ait: uzun kosumlarda (250 donguluk kart testi)
cihaz isinir ve "Cihaz isindi" uyarisi akisin ortasina duser. Tamam'a basilmazsa
altindaki ekran tiklanamaz ve test alakasiz bir yerde duser.
"""
from appium.webdriver.common.appiumby import AppiumBy

# Metin surumden surume degisebildigi icin (buyuk/kucuk harf, "cihaz cok isindi",
# "sicaklik") tek bir tam metne baglanmiyoruz; govdedeki anahtar kelime araniyor.
CIHAZ_ISINDI = (
    AppiumBy.XPATH,
    "//*[contains(@text, 'ısınd') or contains(@text, 'ısind') or "
    "contains(@text, 'Isind') or contains(@text, 'sıcaklık') or "
    "contains(@text, 'Sıcaklık')]",
)

# Uyarinin onay butonu.
CIHAZ_ISINDI_BTN_TAMAM = (
    AppiumBy.XPATH,
    "//*[contains(@resource-id, ':id/btn_ok') or @text='Tamam' or @text='TAMAM' or "
    "@text='Kapat' or @text='OK']",
)
