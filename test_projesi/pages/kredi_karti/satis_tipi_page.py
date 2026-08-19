"""Kart okutulduktan sonra gelen "Satis Tipi" secim ekrani (Satis / Taksitli / Joker).

Bankanin kendi ekrani (com.sardis.bank.YKB). Paket adi BANKAYA OZGUdur; baska bir
kartla farkli bir paket gelebilir, o yuzden locator'lar mumkun oldugunca METNE dayali.

OPSIYONELDIR: bazi kartlarda akis bu ekrani atlayip dogrudan bir sonrakine gecer.
"""
from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class SatisTipiPage(BasePage):
    TEXT_BASLIK = (
        AppiumBy.XPATH,
        "//*[contains(@resource-id, ':id/tv_header') and @text='Satış Tipi']",
    )
    # Tiklanabilir konteynerin content-desc'i 'Item-0'; gorunen isim tiklanamayan
    # alt tv_name'de, o yuzden metin node'undan ebeveyne ('/..') cikiliyor.
    BTN_SATIS = (AppiumBy.XPATH, "//*[@content-desc='Item-0'] | //*[@text='Satış']/..")

    def gorunuyor_mu(self, timeout=10) -> bool:
        return self.gorunur_mu(self.TEXT_BASLIK, timeout=timeout)

    def satis_sec(self):
        """Ilk secenek olan "Satis"i secer (taksitli/kampanyali degil, duz satis)."""
        self.click(self.BTN_SATIS)
        from pages.kredi_karti.kasiyer_no_page import KasiyerNoPage
        return KasiyerNoPage(self.driver)
