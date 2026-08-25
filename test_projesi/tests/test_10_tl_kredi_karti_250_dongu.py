"""10 TL temassiz kredi karti satisi -> 250 kez tekrar.

Oturum ve robot BIR KEZ acilir, dongu icinde 250 satis kosar. Kart her dongude
raftan alinmaz: ``karti_okut()`` kiskac doluysa karti tekrar almaz, sadece
okutur.

HIZ: opsiyonel ekranlar (satis tipi / kasiyer no / PIN) icin SABIT SURE
BEKLENMEZ. Kart okutulduktan sonra "hangi ekran once cikarsa" yarisi yapilir
(``bekle_biri``) ve cikan ekran islenir; fis ekrani gorununce dongu biter.
Sabit beklemeyle her dongude ~30 sn bosa giderdi (250 dongude ~2 saat).
"""
import logging
import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException, TimeoutException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages import kredi_karti, odeme_al, satis, uyarilar
from run_event.api_logger import get_api_logger
from tests import appium_driver, chappie_entegrasyon
from tests.test_3500_tl_kredi_karti import satis_sekmesine_gec

logger = logging.getLogger(__name__)

TUTAR = "10"
KASIYER_NO = "1"
DONGU_SAYISI = 250
KART_BEKLEME_SURESI = 30
ODEME_BEKLEME_SURESI = 60      # kart okutuldu -> fis ekrani cikana kadar
ISINMA_UYARI_LIMITI = 5        # ayni adimda ust uste bu kadar kapatilirsa vazgec
YOKLAMA_ARALIGI = 0.25         # ekran yoklama sikligi (Appium varsayilani 0.5)

# Rakam tuslarinin element referanslari -- her dongude yeniden ARANMAZ.
_tus_onbellegi = {}


def hizlandir(driver):
    """UiAutomator2'nin komut basina harcadigi bekleme paylarini kisar.

    Varsayilanlar tezgah icin fazla comert: her dokunustan once uygulamanin
    'idle' olmasi 10 sn'ye kadar beklenir (waitForIdleTimeout=10000) ve her
    hareketten sonra 3 sn'lik bir onay payi vardir. Tus basimlarinin yavas
    gorunmesinin ASIL sebebi bu -- tiklamanin kendisi degil.
    """
    driver.update_settings({
        "waitForIdleTimeout": 100,          # varsayilan 10000
        "actionAcknowledgmentTimeout": 100,  # varsayilan 3000
        "keyInjectionDelay": 0,
        "waitForSelectorTimeout": 0,
    })


def rakam_bas(driver, karakter):
    """Numerik tus takimindaki bir rakama basar -- ONBELLEKLI ve ID ONCELIKLI.

    Iki kazanc:
      * ID sorgusu XPath'ten kat kat hizli. pages/satis.rakam() XPath'i 'or'lu
        ve tum sayfa hiyerarsisini tarar; ID native sorguya duser.
      * Tus takimi 250 dongu boyunca AYNI ekranda durdugundan element referansi
        onbellege alinir; sonraki dongulerde arama HIC yapilmaz. Referans
        bayatlarsa (ekran yeniden cizildi) tek seferlik yeniden aranir.

    ID bulunamazsa pages/satis.rakam() fallback'ine dusulur; locator'in metin
    yedegi (surum degisikligi) korunur.
    """
    el = _tus_onbellegi.get(karakter)
    if el is not None:
        try:
            el.click()
            return
        except StaleElementReferenceException:
            _tus_onbellegi.pop(karakter, None)

    try:
        el = driver.find_element(AppiumBy.ID, f"com.tokeninc.ecr:id/tv_{karakter}")
    except NoSuchElementException:
        el = WebDriverWait(driver, 10, poll_frequency=YOKLAMA_ARALIGI).until(
            EC.element_to_be_clickable(satis.rakam(karakter)))
    _tus_onbellegi[karakter] = el
    el.click()


def uyari_varsa_kapat(driver) -> bool:
    """'Cihaz isindi' uyarisi ekrandaysa Tamam'a basar. BEKLEMEZ, tek yoklama.

    Uzun kosumda cihaz isinir ve uyari akisin ORTASINA duser; kapatilmazsa
    altindaki ekran tiklanamaz ve test alakasiz bir adimda dusler.
    """
    if not driver.find_elements(*uyarilar.CIHAZ_ISINDI):
        return False
    logger.warning("'Cihaz ısındı' uyarısı çıktı, Tamam'a basılıyor.")
    tikla(driver, uyarilar.CIHAZ_ISINDI_BTN_TAMAM)
    return True


def tikla(driver, locator, timeout=10):
    WebDriverWait(driver, timeout, poll_frequency=YOKLAMA_ARALIGI).until(
        EC.element_to_be_clickable(locator)).click()


def yaz(driver, locator, metin, timeout=10):
    WebDriverWait(driver, timeout, poll_frequency=YOKLAMA_ARALIGI).until(
        EC.presence_of_element_located(locator)).send_keys(metin)


def gorunuyor_mu(driver, locator, timeout=10) -> bool:
    try:
        WebDriverWait(driver, timeout, poll_frequency=YOKLAMA_ARALIGI).until(
            EC.presence_of_element_located(locator))
        return True
    except TimeoutException:
        return False


def kaybolmasini_bekle(driver, locator, timeout=30) -> bool:
    """Eleman EKRANDAN KAYBOLANA kadar yoklar -- chappie'nin hareketi bitirmesi
    tek basina 'cihaz karti gordu' demek DEGILDIR."""
    bitis = time.time() + timeout
    while time.time() < bitis:
        if not driver.find_elements(*locator):
            return True
        time.sleep(YOKLAMA_ARALIGI)
    return False


def bekle_biri(driver, ekranlar: dict, timeout):
    """Verilen ekranlardan HANGISI ONCE CIKARSA onun adini dondurur, yoksa None.

    Opsiyonel ekranlari tek tek sabit sure beklemek yerine hepsini ayni anda
    yoklar: ekran cikar cikmaz donulur, cikmayan ekran icin sure harcanmaz.
    """
    bitis = time.time() + timeout
    while time.time() < bitis:
        for ad, locator in ekranlar.items():
            if driver.find_elements(*locator):
                return ad
        time.sleep(YOKLAMA_ARALIGI)
    return None


def test_10_tl_kredi_karti_250_kez():
    driver = appium_driver.baslat()
    hizlandir(driver)
    chappie = chappie_entegrasyon.baslat()
    kayit = get_api_logger()
    try:
        for dongu in range(1, DONGU_SAYISI + 1):
            baslangic = time.time()
            logger.info("=" * 70)
            logger.info("DÖNGÜ %d/%d -- %s TL temassız satış", dongu, DONGU_SAYISI, TUTAR)
            logger.info("=" * 70)

            # Cihaz isinma uyarisi onceki dongunun sonunda cikmis olabilir.
            uyari_varsa_kapat(driver)

            # --- Satis ekrani: tutari gir, kalemi sepete at ---
            # Fis basildiktan sonra zaten Satis ekranindayiz; sekmeye yeniden
            # basmak gereksiz bir tur (ilk dongude ana menuden gelinir).
            if not driver.find_elements(*satis.EKRAN):
                satis_sekmesine_gec(driver)
            for rakam in TUTAR:
                rakam_bas(driver, rakam)

            kisimlar = driver.find_elements(*satis.KISIM_KARTLARI)
            assert kisimlar, f"HATA (döngü {dongu}): Seçilecek kısım bulunamadı!"
            kisimlar[0].click()

            # --- Devam -> Odeme al -> Kredi K. ---
            tikla(driver, satis.BTN_DEVAM)
            tikla(driver, odeme_al.BTN_KREDI_KARTI)

            # --- CHAPPIE: kart okutma ekrani ACILINCA okut ---
            # Grup kapama onayi CIKABILIR; kart ekraniyla yaristiriliyor ki
            # cikmadigi dongulerde bosa beklenmesin.
            oncesi = {
                "isindi": uyarilar.CIHAZ_ISINDI,
                "grup_kapama": kredi_karti.GRUP_KAPAMA_BASLIK,
                "kart": kredi_karti.KART_OKUTMA_MESAJI,
            }
            isinma_sayaci = 0
            while True:
                ekran = bekle_biri(driver, oncesi, timeout=15)
                if ekran == "isindi":
                    isinma_sayaci += 1
                    assert isinma_sayaci <= ISINMA_UYARI_LIMITI, (
                        f"HATA (döngü {dongu}): 'Cihaz ısındı' uyarısı "
                        f"{ISINMA_UYARI_LIMITI} kez kapatıldı ama geri geliyor -- "
                        "cihazın soğuması gerekiyor."
                    )
                    uyari_varsa_kapat(driver)
                    continue                    # uyari tekrar cikabilir, listede kalir
                if ekran == "grup_kapama":
                    tikla(driver, kredi_karti.GRUP_KAPAMA_BTN_TAMAM)
                    oncesi.pop("grup_kapama")
                    continue
                break
            assert ekran == "kart", (
                f"HATA (döngü {dongu}): 'Lütfen kartı okutun' ekranı açılmadı!"
            )

            chappie.karti_okut()          # kart kıskaçtaysa raftan almaz, sadece okutur
            assert kaybolmasini_bekle(driver, kredi_karti.KART_OKUTMA_MESAJI,
                                      timeout=KART_BEKLEME_SURESI), (
                f"HATA (döngü {dongu}): kart okutuldu ama ekran kapanmadı."
            )

            # --- Kart sonrasi ekranlar: hangisi cikarsa o islenir ---
            # Satis tipi / kasiyer no / PIN OPSIYONEL, sirasi da degisebilir.
            # Fis ekrani cikinca akis biter.
            sonraki = {
                "isindi": uyarilar.CIHAZ_ISINDI,
                "satis_tipi": kredi_karti.SATIS_TIPI_BASLIK,
                "kasiyer": kredi_karti.KASIYER_NO_ETIKET,
                "pin": kredi_karti.PIN_MESAJI,
                "fis": kredi_karti.IS_YERI_NUSHASI_BASLIK,
            }
            pin_girildi = False
            isinma_sayaci = 0
            while True:
                ekran = bekle_biri(driver, sonraki, timeout=ODEME_BEKLEME_SURESI)
                assert ekran, (
                    f"HATA (döngü {dongu}): kart okutuldu ama ne PIN ne de "
                    "'İş yeri nüshası basılacak' ekranı çıktı -- işlem takılmış "
                    "ya da banka reddetmiş olabilir."
                )
                if ekran == "isindi":
                    isinma_sayaci += 1
                    assert isinma_sayaci <= ISINMA_UYARI_LIMITI, (
                        f"HATA (döngü {dongu}): 'Cihaz ısındı' uyarısı "
                        f"{ISINMA_UYARI_LIMITI} kez kapatıldı ama geri geliyor -- "
                        "cihazın soğuması gerekiyor."
                    )
                    uyari_varsa_kapat(driver)
                    continue                    # listeden DUSURULMEZ: tekrar cikabilir
                if ekran == "satis_tipi":
                    tikla(driver, kredi_karti.SATIS_TIPI_BTN_SATIS)
                elif ekran == "kasiyer":
                    yaz(driver, kredi_karti.KASIYER_NO_INPUT, KASIYER_NO)
                    tikla(driver, kredi_karti.KASIYER_NO_BTN_TAMAM)
                elif ekran == "pin":
                    # PIN'i APPIUM GIREMEZ: odeme klavyeleri enjekte dokunusu yok sayar.
                    chappie.pin_gir()
                    assert kaybolmasini_bekle(driver, kredi_karti.PIN_MESAJI,
                                              timeout=KART_BEKLEME_SURESI), (
                        f"HATA (döngü {dongu}): PIN girildi ama PIN ekranı kapanmadı."
                    )
                    pin_girildi = True
                else:                                   # fis
                    tikla(driver, kredi_karti.IS_YERI_NUSHASI_BTN_YAZDIR)
                    break
                # Islenen ekran kapanmadan tekrar yoklarsak ayni ekrani ikinci kez
                # yakalariz; listeden dusuruluyor.
                sonraki.pop(ekran)

            assert gorunuyor_mu(driver, satis.EKRAN, timeout=60), (
                f"HATA (döngü {dongu}): Fiş basıldıktan sonra Satış ekranına dönülemedi."
            )
            logger.info("Döngü %d/%d bitti -- %.1f sn, PIN: %s",
                        dongu, DONGU_SAYISI, time.time() - baslangic,
                        "girildi" if pin_girildi else "istenmedi")
            kayit.log_step_passed(f"Döngü {dongu}/{DONGU_SAYISI}: {TUTAR} TL ödendi.")

    finally:
        # Kart kıskaçta unutulursa BIR SONRAKI koşumun ilk hareketi raftaki karta çarpar.
        try:
            chappie_entegrasyon.kapat(chappie)
        except Exception as hata:
            logger.warning("Robot kapatılamadı: %s", hata)
        appium_driver.kapat(driver)
