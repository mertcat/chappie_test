"""Satis ekrani locator'lari -- com.tokeninc.ecr paketi."""
from appium.webdriver.common.appiumby import AppiumBy

# Girilen tutarin gosterildigi alan.
TUTAR = (AppiumBy.ID, "com.tokeninc.ecr:id/tv_amount")

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
EKRAN = (
    AppiumBy.XPATH,
    "//*[@resource-id='com.tokeninc.ecr:id/tab_layout'] | "
    "//*[@content-desc='Hızlı satış' or @content-desc='Kayıtlı ürünler']",
)


def rakam(karakter: str):
    """Numerik tus takimindaki bir rakam tusunun locator'i.

    Metin fallback'i tv_amount'i ACIKCA DISLAR: girilmekte olan tutar tam olarak
    basilmak istenen rakama esitse (tv_amount "3" gosterirken tekrar "3" tusuna
    basmak) o alan da @text ile eslesir; tiklanamaz oldugu icin basilan rakam
    sessizce kaybolur.
    """
    return (
        AppiumBy.XPATH,
        f"//*[@resource-id='com.tokeninc.ecr:id/tv_{karakter}' or "
        f"(@text='{karakter}' and @resource-id!='com.tokeninc.ecr:id/tv_amount')]",
    )
