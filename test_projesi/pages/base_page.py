"""Tum sayfa siniflarinin atasi -- Appium ile konusan tek yer.

Sayfa siniflari ekrani TANIR (locator'lar, o ekranda yapilabilecekler);
Appium'un ayrintilariyla (bekleme, stale element, timeout) ugrasmaz. O is burada.
"""
import logging

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


class BasePage:
    # Kagit yok / yazici kapagi acik (H70). Sistem seviyesinde bir uyaridir:
    # hangi uygulama yazdirmaya calisirsa calissin cikabilir, o yuzden tek bir
    # sayfaya degil hepsinin paylastigi bu sinifa ait.
    YAZICI_HATA_BASLIK = (
        AppiumBy.XPATH,
        "//*[@resource-id='com.token.v1.os.launcher:id/tv_title' or "
        "@text='Kağıt yok yada yazıcı kapağı açılmış']",
    )

    def __init__(self, driver):
        self.driver = driver

    def find_element(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )

    def find_elements(self, locator, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
        except TimeoutException:
            return []
        return self.driver.find_elements(*locator)

    def click(self, locator, timeout=10):
        WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        ).click()

    def send_keys(self, locator, text, timeout=10):
        self.find_element(locator, timeout).send_keys(text)

    def get_text(self, locator, timeout=10):
        return self.find_element(locator, timeout).text

    def gorunur_mu(self, locator, timeout=10) -> bool:
        """Ekran/eleman verilen sure icinde belirdi mi. HATA FIRLATMAZ."""
        try:
            self.find_element(locator, timeout=timeout)
            return True
        except TimeoutException:
            return False

    def yazdirmayi_bekle(self, hedef_locator, hedef_aciklamasi, timeout=30,
                         kagit_bekleme_suresi=300):
        """Fiziksel yazdirma bitip hedef ekranin belirmesini bekler.

        Yazdirma sirasinda kagit biterse (H70) cihaz hedef ekrani HIC gostermez.
        Bu durumda hata verip dusmek yerine kagit takilmasi beklenir -- donanim
        eksigi bir urun hatasi degildir.
        """
        if self.gorunur_mu(hedef_locator, timeout=timeout):
            return True

        if self.gorunur_mu(self.YAZICI_HATA_BASLIK, timeout=2):
            logger.warning("YAZICI HATASI: kağıt yok ya da kapak açık. "
                           "Kağıt takılması bekleniyor (en fazla %d sn).",
                           kagit_bekleme_suresi)
            if not self.gorunur_mu(hedef_locator, timeout=kagit_bekleme_suresi):
                raise Exception(
                    f"HATA: YAZICI HATASI çözülmedi -- {hedef_aciklamasi} belirmedi. "
                    "Kağıt takıp yazıcı kapağını kapatın."
                )
            return True

        raise Exception(f"HATA: {hedef_aciklamasi} {timeout} sn içinde belirmedi!")
