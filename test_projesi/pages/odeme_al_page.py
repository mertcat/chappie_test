"""Odeme al ekrani -- odeme yontemi secilir.

Bu ekran com.tokeninc.sardis.paymentgateway paketine aittir.
"""
import logging

from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class OdemeAlPage(BasePage):
    # Odeme tipi kartlari; content-desc birincil, gorunen metin fallback.
    # Metin node'u tiklanabilir degil, o yuzden ebeveyne ('/..') cikiliyor.
    BTN_KREDI_KARTI = (
        AppiumBy.XPATH,
        "//*[@content-desc='payment_type_3'] | //*[@text='Kredi K.']/..",
    )

    def kredi_karti_ile_ode(self):
        """'Kredi K.'ye basar ve kart okutma ekranini dondurur.

        Tiklamadan HEMEN SONRA bankanin "Grup Kapama Yapilacaktir" onayi
        CIKABILIR -- her zaman degil, opsiyonel. Cikarsa 'Tamam'a basilir ve
        akis normal sekilde kart okutma ekranina devam eder.
        """
        logger.info("Ödeme al ekranında 'Kredi K.' seçiliyor.")
        self.click(self.BTN_KREDI_KARTI)

        from pages.kredi_karti.grup_kapama_page import GrupKapamaPage
        if GrupKapamaPage(self.driver).tamam_tikla_varsa(timeout=5):
            logger.info("'Grup Kapama Yapılacaktır' onayı çıktı, 'Tamam'a basıldı.")

        from pages.kredi_karti.kart_okutma_page import KartOkutmaPage
        return KartOkutmaPage(self.driver)
