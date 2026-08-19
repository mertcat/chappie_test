"""Kasiyer No giris ekrani. SatisTipiPage ile AYNI banka paketine ait.

ONEMLI -- ONAY BUTONU BASTA YOK: 'Kasiyer No Tamam' alan BOSKEN ust barda hic
yok, yalnizca deger girildikten SONRA beliriyor.

NOT: bu ekranda ust bar basligi hala "Satis Tipi" yaziyor -- giris katmani bir
oncekinin uzerine biniyor. Bu yuzden ekranin isareti baslik DEGIL, alanin kendi
etiketi.

OPSIYONELDIR: bazi kartlarda akis bu ekrani atlar.
"""
from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class KasiyerNoPage(BasePage):
    TEXT_ETIKET = (
        AppiumBy.XPATH,
        "//*[contains(@resource-id, ':id/et_hint') or @text='Kasiyer No']",
    )
    # Giris kutusunun kendi resource-id'si YOK; content-desc ile hedefleniyor.
    INPUT_KASIYER_NO = (AppiumBy.ACCESSIBILITY_ID, "Input-0")
    BTN_TAMAM = (
        AppiumBy.XPATH,
        "//*[contains(@resource-id, ':id/btn_ok') or @text='Kasiyer No Tamam']",
    )

    def gorunuyor_mu(self, timeout=10) -> bool:
        return self.gorunur_mu(self.TEXT_ETIKET, timeout=timeout)

    def kasiyer_no_gir_ve_onayla(self, kasiyer_no: str):
        """Kasiyer no'yu girer ve onaylar; onay butonu ancak alan doluyken belirir."""
        self.send_keys(self.INPUT_KASIYER_NO, kasiyer_no)
        self.click(self.BTN_TAMAM)
        from pages.kredi_karti.pin_girisi_page import PinGirisiPage
        return PinGirisiPage(self.driver)
