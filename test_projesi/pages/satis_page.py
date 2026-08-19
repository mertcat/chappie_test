"""Satis ekrani -- tutar girilir, kisim secilir, Devam'a basilir.

Bu ekran com.tokeninc.ecr paketine aittir.
"""
import logging

from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class SatisPage(BasePage):
    # Girilen tutarin gosterildigi alan.
    TEXT_TUTAR = (AppiumBy.ID, "com.tokeninc.ecr:id/tv_amount")
    # Ekranda listelenen kisim (kategori) kartlari. id degisirse kartlarin
    # content-desc'i ("category_item_N") fallback olarak kullaniliyor.
    KISIM_KARTLARI = (
        AppiumBy.XPATH,
        "//*[@resource-id='com.tokeninc.ecr:id/category'] | "
        "//*[starts-with(@content-desc, 'category_item_')]",
    )
    # Odeme al ekranina gecis.
    BTN_DEVAM = (AppiumBy.ID, "com.tokeninc.ecr:id/btn_pay")
    # Ekranin kendi isareti -- yazdirma bitip buraya donuldugunu anlamak icin.
    TAB_LAYOUT = (
        AppiumBy.XPATH,
        "//*[@resource-id='com.tokeninc.ecr:id/tab_layout'] | "
        "//*[@content-desc='Hızlı satış' or @content-desc='Kayıtlı ürünler']",
    )

    def _rakam_locator(self, karakter: str):
        """Numerik tus takimindaki bir rakam tusu.

        Metin fallback'i tv_amount'i ACIKCA DISLAR: girilmekte olan tutar tam
        olarak basilmak istenen rakama esitse (tv_amount "3" gosterirken tekrar
        "3" tusuna basmak) o alan da @text ile eslesir ve tiklanamaz oldugu icin
        basilan rakam sessizce kaybolur.
        """
        return (
            AppiumBy.XPATH,
            f"//*[@resource-id='com.tokeninc.ecr:id/tv_{karakter}' or "
            f"(@text='{karakter}' and @resource-id!='com.tokeninc.ecr:id/tv_amount')]",
        )

    def tutar_gir(self, tutar: str):
        """Tutardaki her karaktere sirayla basar: "3500" -> 3, 5, 0, 0."""
        logger.info("Tutar giriliyor: %s", tutar)
        for karakter in tutar:
            self.click(self._rakam_locator(karakter))

    def tutari_oku(self) -> str:
        return self.get_text(self.TEXT_TUTAR)

    def ilk_kismi_sec(self):
        """Listelenen kisimlardan ilkine tiklar -- sepete kalem ekler."""
        kisimlar = self.find_elements(self.KISIM_KARTLARI)
        if not kisimlar:
            raise Exception("HATA: Ekranda seçilecek herhangi bir kısım bulunamadı!")
        logger.info("İlk kısım seçiliyor.")
        kisimlar[0].click()

    def devam_tikla(self, timeout=10):
        """'Devam'a basar ve Odeme al ekranini dondurur."""
        self.click(self.BTN_DEVAM, timeout=timeout)
        from pages.odeme_al_page import OdemeAlPage
        return OdemeAlPage(self.driver)

    def satis_ekranina_donusunu_bekle(self, timeout=60):
        """Yazdirma bitip Satis ekranina donulmesini bekler (kagit hatasi dahil)."""
        self.yazdirmayi_bekle(self.TAB_LAYOUT, "Satış ekranı", timeout=timeout)
        return self
