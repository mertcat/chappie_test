"""Odeme al ekrani locator'lari -- com.tokeninc.sardis.paymentgateway paketi."""
from appium.webdriver.common.appiumby import AppiumBy

# Odeme tipi karti. content-desc birincil, gorunen metin fallback; metin node'u
# tiklanabilir olmadigi icin ebeveyne ('/..') cikiliyor.
BTN_KREDI_KARTI = (
    AppiumBy.XPATH,
    "//*[@content-desc='payment_type_3'] | //*[@text='Kredi K.']/..",
)
