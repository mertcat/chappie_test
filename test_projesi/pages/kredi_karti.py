"""Kredi karti akisindaki ekranlarin locator'lari.

UC AYRI PAKET var, karistirmayin:
  com.tokeninc.cardservice            kart okutma, PIN girisi
  com.sardis.bank.YKB                 grup kapama, satis tipi, kasiyer no (BANKAYA OZGU)
  com.tokeninc.sardis.paymentgateway  is yeri nushasi
"""
from appium.webdriver.common.appiumby import AppiumBy

# --- Grup kapama: 'Kredi K.'ye basildiktan sonra CIKABILIR (her zaman degil) ---
GRUP_KAPAMA_BASLIK = (
    AppiumBy.XPATH,
    "//*[@resource-id='com.sardis.bank.YKB:id/tv_title' or @text='Grup Kapama Yapılacaktır']",
)
GRUP_KAPAMA_BTN_TAMAM = (
    AppiumBy.XPATH,
    "//*[@resource-id='com.sardis.bank.YKB:id/btn_ok' or @text='Tamam']",
)

# --- Kart okutma ---
# DIKKAT -- id TEK BASINA AYIRT EDICI DEGIL: 'readText' id'si AYNI pakette PIN
# ekrani tarafindan da FARKLI bir metinle kullaniliyor. Bu yuzden 'or' DEGIL 'and'.
KART_OKUTMA_MESAJI = (
    AppiumBy.XPATH,
    "//*[@resource-id='com.tokeninc.cardservice:id/readText' "
    "and @text='Lütfen kartı okutun']",
)
KART_OKUTMA_TUTAR = (AppiumBy.ID, "com.tokeninc.cardservice:id/amount")

# --- Satis tipi (OPSIYONEL: bazi kartlarda cikmaz) ---
SATIS_TIPI_BASLIK = (
    AppiumBy.XPATH,
    "//*[contains(@resource-id, ':id/tv_header') and @text='Satış Tipi']",
)
# Tiklanabilir konteynerin content-desc'i 'Item-0'; gorunen isim tiklanamayan alt
# tv_name'de, o yuzden metin node'undan ebeveyne ('/..') cikiliyor.
SATIS_TIPI_BTN_SATIS = (
    AppiumBy.XPATH,
    "//*[@content-desc='Item-0'] | //*[@text='Satış']/..",
)

# --- Kasiyer no (OPSIYONEL) ---
# Bu ekranda ust bar basligi HALA "Satis Tipi" yaziyor (giris katmani oncekinin
# uzerine biniyor), o yuzden ekranin isareti baslik DEGIL alanin kendi etiketi.
KASIYER_NO_ETIKET = (
    AppiumBy.XPATH,
    "//*[contains(@resource-id, ':id/et_hint') or @text='Kasiyer No']",
)
# Giris kutusunun kendi resource-id'si YOK; content-desc ile hedefleniyor.
KASIYER_NO_INPUT = (AppiumBy.ACCESSIBILITY_ID, "Input-0")
# Bu buton alan BOSKEN HIC YOK, yalnizca deger girildikten SONRA beliriyor.
KASIYER_NO_BTN_TAMAM = (
    AppiumBy.XPATH,
    "//*[contains(@resource-id, ':id/btn_ok') or @text='Kasiyer No Tamam']",
)

# --- PIN girisi (OPSIYONEL: dusuk tutarli/temassiz islemde cikmayabilir) ---
# Kart okutma ile AYNI 'readText' id'si -- yine 'and' kullaniliyor.
PIN_MESAJI = (
    AppiumBy.XPATH,
    "//*[contains(@resource-id, ':id/readText') and @text='PIN girişi bekleniyor']",
)

# --- Is yeri nushasi ---
# DIKKAT -- id TEK BASINA AYIRT EDICI DEGIL: tv_title_info id'si AYNI pakette
# 'Odeme alindi' ekraninda DA kullaniliyor. Bu yuzden 'or' DEGIL 'and'.
IS_YERI_NUSHASI_BASLIK = (
    AppiumBy.XPATH,
    "//*[contains(@resource-id, ':id/tv_title_info') "
    "and @text='İş yeri nüshası basılacak']",
)
IS_YERI_NUSHASI_BTN_YAZDIR = (
    AppiumBy.XPATH,
    "//*[@resource-id='com.tokeninc.sardis.paymentgateway:id/btn_ok' or @text='Yazdır']",
)
