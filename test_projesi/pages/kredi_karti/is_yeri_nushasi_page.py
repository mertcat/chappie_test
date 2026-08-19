"""Kart odemesi onaylandiktan sonra gelen "Is yeri nushasi basilacak" ekrani.

Odeme al ile AYNI pakete ait (com.tokeninc.sardis.paymentgateway).

NOT: 'Yazdir'a BASILMASA da ekran kendiliginden kapanip Satis ekranina donuyor.
Yine de basmak fis ciktisini garanti ettigi icin tercih ediliyor -- ekran erken
kapanmissa bu bir HATA DEGILDIR.

DIKKAT -- id TEK BASINA AYIRT EDICI DEGIL: tv_title_info id'si AYNI pakette
'Odeme alindi' ekraninda DA kullaniliyor. Bu yuzden 'or' DEGIL 'and'.
"""
import logging

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class IsYeriNushasiPage(BasePage):
    TEXT_BASLIK = (
        AppiumBy.XPATH,
        "//*[contains(@resource-id, ':id/tv_title_info') "
        "and @text='İş yeri nüshası basılacak']",
    )
    BTN_YAZDIR = (
        AppiumBy.XPATH,
        "//*[@resource-id='com.tokeninc.sardis.paymentgateway:id/btn_ok' or @text='Yazdır']",
    )

    def gorunuyor_mu(self, timeout=20) -> bool:
        return self.gorunur_mu(self.TEXT_BASLIK, timeout=timeout)

    def yazdir_tikla_varsa(self, timeout=10) -> bool:
        """'Yazdir' varsa basar; ekran erken kapanmissa sessizce False doner."""
        try:
            self.click(self.BTN_YAZDIR, timeout=timeout)
            logger.info("İş yeri nüshası ekranında 'Yazdır'a basıldı.")
            return True
        except TimeoutException:
            logger.info("İş yeri nüshası ekranı görünmedi/erken kapandı, 'Yazdır' atlandı.")
            return False

    def satisa_don(self, timeout=10):
        """'Yazdir'a basar, fis basilip Satis ekranina donulmesini bekler."""
        self.yazdir_tikla_varsa(timeout=timeout)
        from pages.satis_page import SatisPage
        return SatisPage(self.driver).satis_ekranina_donusunu_bekle()
