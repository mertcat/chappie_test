"""3500 TL satis -> kart NFC ile okutulur -> PIN girilir -> fis basilir.

Bastan sona elle mudahale gerektirmez: karti chappie okutur, PIN'i chappie girer.

Akisin TAMAMI bu dosyada. pages/ altinda yalnizca locator'lar var; orada hicbir
akis yok. Yeni bir senaryo yazmak isteyen buradaki adimlari kopyalayip degistirir.
"""
import logging
import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages import ana_menu, kredi_karti, odeme_al, satis
from run_event.api_logger import get_api_logger

logger = logging.getLogger(__name__)

TUTAR = "3500"
KASIYER_NO = "1"
KART_BEKLEME_SURESI = 30
PIN_BEKLEME_SURESI = 30


# --------------------------------------------------------------------------------------
# Appium yardimcilari
# --------------------------------------------------------------------------------------
def tikla(driver, locator, timeout=10):
    WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator)).click()


def yaz(driver, locator, metin, timeout=10):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)).send_keys(metin)


def metni_oku(driver, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)).text


def gorunuyor_mu(driver, locator, timeout=10) -> bool:
    """Ekran/eleman verilen sure icinde belirdi mi. HATA FIRLATMAZ."""
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
        return True
    except TimeoutException:
        return False


def kaybolmasini_bekle(driver, locator, timeout=30, kontrol_araligi=1) -> bool:
    """Eleman EKRANDAN KAYBOLANA kadar kisa araliklarla yoklar.

    Chappie'nin hareketi tamamlamasi TEK BASINA "cihaz karti gordu" demek
    DEGILDIR; karti gercekten okudugunu ancak ekranin kapanmasindan anlariz.
    """
    kalan = timeout
    while kalan > 0:
        if not driver.find_elements(*locator):
            return True
        time.sleep(kontrol_araligi)
        kalan -= kontrol_araligi
    return False


def satis_sekmesine_gec(driver, timeout=10):
    """Ana menuden Satis sekmesine gecer ve gercekten gecildigini dogrular.

    Cihazda ara sira Android'in KENDI navigasyon cubugu uygulamanin alt
    navigasyon barinin uzerine binip dokunusu yutuyor; bu durumda tiklama
    hicbir sey yapmaz. Bir kez BACK ile temizleyip tekrar deniyoruz.
    """
    for deneme in (1, 2):
        tikla(driver, ana_menu.NAV_SATIS)
        if gorunuyor_mu(driver, satis.EKRAN, timeout=timeout):
            return
        logger.warning("Satış ekranına geçilemedi (%d/2) -- sistem navigasyon çubuğu "
                       "araya girmiş olabilir, BACK ile temizleniyor.", deneme)
        driver.press_keycode(4)          # KEYCODE_BACK

    raise Exception(
        "HATA: BACK ile temizleyip tekrar denemeye rağmen Satış ekranına geçilemedi."
    )


# --------------------------------------------------------------------------------------
# Test
# --------------------------------------------------------------------------------------
def test_3500_tl_kredi_karti_ile_odeme(driver, chappie):
    kayit = get_api_logger()
    try:
        # --- 1) Ana menuden Satis ekranina gec ---
        # Appium oturumu launcher'in ANA MENU ekraninda aciliyor; rakam tus takimi
        # orada YOK. Once Satis sekmesine gecilmesi sart.
        satis_sekmesine_gec(driver)
        kayit.log_step_passed("Satış ekranına geçildi.")

        # --- 2) 3500 TL'lik kalem: rakamlara sirayla bas, sonra ilk kisma tikla ---
        for rakam in TUTAR:
            tikla(driver, satis.rakam(rakam))

        kisimlar = driver.find_elements(*satis.KISIM_KARTLARI)
        assert kisimlar, "HATA: Ekranda seçilecek herhangi bir kısım bulunamadı!"
        kisimlar[0].click()
        kayit.log_step_passed(f"{TUTAR} TL'lik kalem sepete eklendi.")

        # --- 3) Devam -> Odeme al -> Kredi K. ---
        tikla(driver, satis.BTN_DEVAM)
        tikla(driver, odeme_al.BTN_KREDI_KARTI)

        # Bankanin "Grup Kapama Yapilacaktir" onayi CIKABILIR -- her zaman degil.
        if gorunuyor_mu(driver, kredi_karti.GRUP_KAPAMA_BASLIK, timeout=5):
            tikla(driver, kredi_karti.GRUP_KAPAMA_BTN_TAMAM)
            logger.info("'Grup Kapama Yapılacaktır' onayı çıktı, 'Tamam'a basıldı.")

        # --- 4) CHAPPIE: karti NFC'ye okut ---
        assert gorunuyor_mu(driver, kredi_karti.KART_OKUTMA_MESAJI), (
            "HATA: 'Lütfen kartı okutun' ekranı açılmadı!"
        )
        logger.info("Kart okutma ekranı açıldı (tutar: %s).",
                    metni_oku(driver, kredi_karti.KART_OKUTMA_TUTAR))

        # Kart erken okutulursa cihaz gormez; ekranin acildigi YUKARIDA
        # dogrulandiktan SONRA hareket ettiriliyor.
        chappie.karti_okut()

        assert kaybolmasini_bekle(driver, kredi_karti.KART_OKUTMA_MESAJI,
                                  timeout=KART_BEKLEME_SURESI), (
            "HATA: chappie kartı okuttu ama 'Lütfen kartı okutun' ekranı kapanmadı -- "
            "kart okuyucuya yeterince yaklaşmamış olabilir."
        )
        kayit.log_step_passed("Kart chappie tarafından okutuldu.")

        # --- 5) Satis Tipi / Kasiyer No -- IKISI DE OPSIYONEL ---
        # Bazi kartlarda akis bu ekranlari atlar; cikmamalari hata degildir.
        if gorunuyor_mu(driver, kredi_karti.SATIS_TIPI_BASLIK, timeout=10):
            tikla(driver, kredi_karti.SATIS_TIPI_BTN_SATIS)
            logger.info("Satış Tipi ekranında 'Satış' seçildi.")

        if gorunuyor_mu(driver, kredi_karti.KASIYER_NO_ETIKET, timeout=10):
            yaz(driver, kredi_karti.KASIYER_NO_INPUT, KASIYER_NO)
            # Onay butonu alan BOSKEN yok, ancak deger girildikten SONRA beliriyor.
            tikla(driver, kredi_karti.KASIYER_NO_BTN_TAMAM)
            logger.info("Kasiyer No '%s' girildi.", KASIYER_NO)

        # --- 6) CHAPPIE: PIN gir ---
        # PIN'i APPIUM GIREMEZ: odeme klavyeleri sertifikasyon geregi enjekte
        # dokunuslari yok sayar. Chappie tuslara fiziksel bastigi icin kisit onu
        # baglamaz. Bu ekran da OPSIYONEL.
        if gorunuyor_mu(driver, kredi_karti.PIN_MESAJI, timeout=15):
            chappie.pin_gir()
            assert kaybolmasini_bekle(driver, kredi_karti.PIN_MESAJI,
                                      timeout=PIN_BEKLEME_SURESI), (
                "HATA: chappie PIN'i girdi ama PIN ekranı kapanmadı -- tuşlara "
                "isabet edilememiş ya da onay (tik) tuşuna basılamamış olabilir."
            )
            kayit.log_step_passed("PIN chappie tarafından girildi ve onaylandı.")
        else:
            logger.info("PIN ekranı çıkmadı (bu ödeme için gerekmemiş olabilir).")

        # --- 7) Fis bas ve Satis ekranina don ---
        assert gorunuyor_mu(driver, kredi_karti.IS_YERI_NUSHASI_BASLIK, timeout=20), (
            "HATA: Ödeme sonrası 'İş yeri nüshası basılacak' ekranı çıkmadı -- "
            "ödeme işlenmemiş ya da banka işlemi reddetmiş olabilir."
        )
        tikla(driver, kredi_karti.IS_YERI_NUSHASI_BTN_YAZDIR)

        assert gorunuyor_mu(driver, satis.EKRAN, timeout=60), (
            "HATA: Fiş basıldıktan sonra Satış ekranına dönülemedi -- kağıt bitmiş "
            "ya da yazıcı kapağı açık olabilir."
        )
        kayit.log_step_passed(f"{TUTAR} TL kredi kartı ile ödendi, fiş basıldı.")

    finally:
        # --- 8) Kart rafa donsun ---
        # Kart cihazda ya da kiskacta unutulursa BIR SONRAKI kosumun ilk hareketi
        # raftaki karta carpar. Test dusse de calismasi sart.
        try:
            chappie.temizle()
        except Exception as hata:
            logger.warning("Robot temizliği yapılamadı: %s", hata)
