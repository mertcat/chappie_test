"""'PIN girisi bekleniyor' ekrani. KartOkutmaPage ile AYNI pakete ait.

PIN'i APPIUM GIREMEZ: odeme klavyeleri kart sertifikasyonu geregi ENJEKTE
edilmis dokunuslari (Appium click, koordinat dokunusu) yok sayar. Bu yuzden
PIN'i chappie girer -- tuslara fiziksel bastigi icin o kisit onu baglamaz.

Bu sayfa PIN GIRMEZ, yalnizca ekranin kapanmasini BEKLER.

OPSIYONELDIR: temassiz/dusuk tutarli islemlerde kart PIN istemeyebilir.
"""
import logging
import time

from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class PinGirisiPage(BasePage):
    # 'readText' id'si AYNI pakette kart okutma ekrani tarafindan da FARKLI bir
    # metinle kullaniliyor -- bu yuzden 'or' DEGIL 'and' (bkz. KartOkutmaPage).
    TEXT_PIN_MESAJI = (
        AppiumBy.XPATH,
        "//*[contains(@resource-id, ':id/readText') and @text='PIN girişi bekleniyor']",
    )

    def gorunuyor_mu(self, timeout=5) -> bool:
        return self.gorunur_mu(self.TEXT_PIN_MESAJI, timeout=timeout)

    def girilmesini_bekle(self, timeout=60, kontrol_araligi=1) -> bool:
        """Ekran KAYBOLANA kadar kisa araliklarla yoklar.

        KartOkutmaPage.kart_okutulmasini_bekle ILE AYNI sozlesme: hata firlatmaz,
        ekran kapandiysa True doner. Ekranin kapanmasi TEK BASINA "PIN dogru
        girildi" demek degildir; karar cagirana ait.
        """
        kalan = timeout
        while kalan > 0:
            if not self.driver.find_elements(*self.TEXT_PIN_MESAJI):
                logger.info("PIN ekranı kapandı, akış devam ediyor.")
                return True
            time.sleep(kontrol_araligi)
            kalan -= kontrol_araligi

        logger.warning("PIN %d sn içinde girilmedi.", timeout)
        return False
