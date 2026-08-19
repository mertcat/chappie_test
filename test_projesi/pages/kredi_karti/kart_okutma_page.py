"""'Lutfen karti okutun' ekrani.

Bu ekran com.tokeninc.cardservice paketine aittir -- Odeme al ekraninin
(com.tokeninc.sardis.paymentgateway) ve banka akisinin (com.sardis.bank.YKB)
IKISINDEN DE farkli, UCUNCU bir paket.

Bu sayfa karti OKUTMAZ, yalnizca BEKLER. Okutma isi chappie'nindir; komutu
testin kendisi verir (bkz. tests/chappie_entegrasyon.py).
"""
import logging
import time

from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class KartOkutmaPage(BasePage):
    # Ekranin kendi isareti: "Lutfen karti okutun" metnini tasiyan TextView.
    # DIKKAT -- id TEK BASINA AYIRT EDICI DEGIL: 'readText' id'si AYNI pakette
    # PIN ekrani tarafindan da FARKLI bir metinle kullaniliyor. Bu yuzden
    # 'or' DEGIL 'and'.
    TEXT_OKUTMA_MESAJI = (
        AppiumBy.XPATH,
        "//*[@resource-id='com.tokeninc.cardservice:id/readText' "
        "and @text='Lütfen kartı okutun']",
    )
    TEXT_TUTAR = (AppiumBy.ID, "com.tokeninc.cardservice:id/amount")

    def gorunuyor_mu(self, timeout=10) -> bool:
        return self.gorunur_mu(self.TEXT_OKUTMA_MESAJI, timeout=timeout)

    def tutari_oku(self) -> str:
        """Ekranda gorunen odenecek tutari HAM haliyle dondurur (or. '3.500,00 ₺')."""
        return self.get_text(self.TEXT_TUTAR)

    def kart_okutulmasini_bekle(self, timeout=30, kontrol_araligi=1) -> bool:
        """Ekran KAYBOLANA kadar kisa araliklarla yoklar.

        Chappie'nin hareketi tamamlamasi TEK BASINA "cihaz karti gordu" demek
        DEGILDIR; karti gerçekten okudugunu ancak bu ekranin kapanmasindan
        anlariz. Bu yuzden komut verildikten SONRA da burasi calisir.

        Donus: ekran kapandiysa True, timeout boyunca durmaya devam ettiyse False.
        HATA FIRLATMAZ -- karar cagirana ait.
        """
        kalan = timeout
        while kalan > 0:
            if not self.driver.find_elements(*self.TEXT_OKUTMA_MESAJI):
                logger.info("Kart okutma ekranı kapandı, akış devam ediyor.")
                return True
            time.sleep(kontrol_araligi)
            kalan -= kontrol_araligi

        logger.warning("Kart %d sn içinde okutulmadı.", timeout)
        return False
