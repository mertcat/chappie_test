"""Ana menu (launcher) locator'lari -- com.token.v1.os.launcher paketi.

Appium oturumu bu ekranda aciliyor; Satis ekranina buradan geciliyor.
"""
from appium.webdriver.common.appiumby import AppiumBy

# Alt navigasyon cubugundaki Satis sekmesi. resource-id bir surum
# guncellemesiyle degisirse locator content-desc'e ("Satis") duserek
# calismaya devam eder.
NAV_SATIS = (
    AppiumBy.XPATH,
    "//*[contains(@resource-id, 'id/menu_do_sale') or @content-desc='Satış']",
)
