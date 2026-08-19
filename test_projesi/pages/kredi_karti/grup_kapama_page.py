"""Bankanin opsiyonel "Grup Kapama Yapilacaktir" onayi.

'Kredi K.'ye basildiktan HEMEN SONRA cikabilir -- her zaman degil.
Bu ekran com.sardis.bank.YKB paketine aittir (bankaya ozgu).
"""
import logging

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class GrupKapamaPage(BasePage):
    TEXT_BASLIK = (
        AppiumBy.XPATH,
        "//*[@resource-id='com.sardis.bank.YKB:id/tv_title' or @text='Grup Kapama Yapılacaktır']",
    )
    BTN_TAMAM = (
        AppiumBy.XPATH,
        "//*[@resource-id='com.sardis.bank.YKB:id/btn_ok' or @text='Tamam']",
    )

    def tamam_tikla_varsa(self, timeout=5) -> bool:
        """Ekran cikarsa 'Tamam'a basar; cikmazsa hicbir sey yapmaz. HATA FIRLATMAZ."""
        if not self.gorunur_mu(self.TEXT_BASLIK, timeout=timeout):
            return False
        try:
            self.click(self.BTN_TAMAM, timeout=timeout)
            return True
        except TimeoutException:
            return False
