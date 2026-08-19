"""3500 TL satis -> kart NFC ile okutulur -> PIN girilir -> fis basilir.

Bastan sona elle mudahale gerektirmez: karti chappie okutur, PIN'i chappie girer.

AKIS
1. Satis ekraninda 3500 yazilir ve ilk kisma tiklanir (sepete kalem eklenir).
2. Devam -> Odeme al -> Kredi K.
3. "Lutfen karti okutun" ekrani beklenir; CHAPPIE karti NFC'ye okutur.
4. Satis Tipi ve Kasiyer No ekranlari (CIKARLARSA) gecilir -- ikisi de opsiyonel.
5. PIN ekrani cikarsa CHAPPIE PIN'i girer.
6. Is yeri nushasi yazdirilir, Satis ekranina donulur.
7. Kart rafa geri konur.
"""
import logging

from pages.kredi_karti.is_yeri_nushasi_page import IsYeriNushasiPage
from pages.kredi_karti.kasiyer_no_page import KasiyerNoPage
from pages.kredi_karti.pin_girisi_page import PinGirisiPage
from pages.kredi_karti.satis_tipi_page import SatisTipiPage
from pages.satis_page import SatisPage

logger = logging.getLogger(__name__)

TUTAR = "3500"
KASIYER_NO = "1"
KART_BEKLEME_SURESI = 30
PIN_BEKLEME_SURESI = 30


def test_3500_tl_kredi_karti_ile_odeme(driver, chappie):
    try:
        # --- 1) 3500 TL'lik kalem ---
        satis = SatisPage(driver)
        satis.tutar_gir(TUTAR)
        satis.ilk_kismi_sec()
        logger.info("%s TL'lik kalem sepete eklendi.", TUTAR)

        # --- 2) Odeme al -> Kredi K. ---
        odeme_al = satis.devam_tikla()
        kart_okutma = odeme_al.kredi_karti_ile_ode()
        assert kart_okutma.gorunuyor_mu(), (
            "HATA: 'Lütfen kartı okutun' ekranı açılmadı!"
        )
        logger.info("Kart okutma ekranı açıldı (tutar: %s).", kart_okutma.tutari_oku())

        # --- 3) CHAPPIE: karti NFC'ye okut ---
        # Kart erken okutulursa cihaz gormez; bu yuzden ekranin acildigi YUKARIDA
        # dogrulandiktan SONRA hareket ettiriliyor.
        chappie.karti_okut()
        # Chappie'nin hareketi bitirmesi TEK BASINA "cihaz karti gordu" demek
        # degildir -- ekranin gercekten kapandigini ayrica dogruluyoruz.
        assert kart_okutma.kart_okutulmasini_bekle(timeout=KART_BEKLEME_SURESI), (
            "HATA: chappie kartı okuttu ama 'Lütfen kartı okutun' ekranı kapanmadı -- "
            "kart okuyucuya yeterince yaklaşmamış olabilir."
        )
        logger.info("Kart okutuldu.")

        # --- 4) Satis Tipi / Kasiyer No -- IKISI DE OPSIYONEL ---
        # Bazi kartlarda akis bu ekranlari atlayip dogrudan PIN'e ya da fise gecer;
        # cikmamalari hata degildir.
        satis_tipi = SatisTipiPage(driver)
        if satis_tipi.gorunuyor_mu(timeout=10):
            satis_tipi.satis_sec()
            logger.info("Satış Tipi ekranında 'Satış' seçildi.")

        kasiyer_no = KasiyerNoPage(driver)
        if kasiyer_no.gorunuyor_mu(timeout=10):
            kasiyer_no.kasiyer_no_gir_ve_onayla(KASIYER_NO)
            logger.info("Kasiyer No '%s' girildi.", KASIYER_NO)

        # --- 5) CHAPPIE: PIN gir ---
        # PIN ekrani da opsiyonel: temassiz/dusuk tutarli islemde kart istemeyebilir.
        pin_girisi = PinGirisiPage(driver)
        if pin_girisi.gorunuyor_mu(timeout=15):
            chappie.pin_gir()
            assert pin_girisi.girilmesini_bekle(timeout=PIN_BEKLEME_SURESI), (
                "HATA: chappie PIN'i girdi ama PIN ekranı kapanmadı -- tuşlara "
                "isabet edilememiş ya da onay (tik) tuşuna basılamamış olabilir."
            )
            logger.info("PIN girildi ve onaylandı.")
        else:
            logger.info("PIN ekranı çıkmadı (bu ödeme için gerekmemiş olabilir).")

        # --- 6) Fis bas ve Satis ekranina don ---
        is_yeri_nushasi = IsYeriNushasiPage(driver)
        assert is_yeri_nushasi.gorunuyor_mu(timeout=20), (
            "HATA: Ödeme sonrası 'İş yeri nüshası basılacak' ekranı çıkmadı -- "
            "ödeme işlenmemiş ya da banka işlemi reddetmiş olabilir."
        )
        is_yeri_nushasi.satisa_don()
        logger.info("%s TL kredi kartı ile ödendi, fiş basıldı.", TUTAR)

    finally:
        # --- 7) Kart rafa donsun ---
        # Kart cihazda ya da kiskacta unutulursa BIR SONRAKI kosumun ilk hareketi
        # raftaki karta carpar. Test dusse de calismasi sart.
        try:
            chappie.temizle()
        except Exception as hata:
            logger.warning("Robot temizliği yapılamadı: %s", hata)
