"""Chappie'nin bu test projesine baglandigi TEK dosya.

DIZIN YERLESIMI -- chappie paketi test projesinin DISINDA durur:

    chappie_test/
    ├── chappie/          <- robotu suren paket (projeden bagimsiz)
    └── test_projesi/     <- bu proje
        ├── pages/
        ├── tests/
        │   └── chappie_entegrasyon.py   (bu dosya)
        └── main.py

Paket disarida oldugu icin import edilebilmesi adina bir ust dizin sys.path'e
ekleniyor (asagida). Boylece ayni chappie klasoru birden cok test projesi
tarafindan paylasilabilir; kopyalanmasi gerekmez.

Test yazan kisi ``chappie`` fixture'ini isteyip komutlari DOGRUDAN yazar;
arada sarmalayici, yama ya da gizli otomatik davranis YOKTUR:

    def test_kart_ile_odeme(driver, chappie):
        kart_okutma = odeme_al.kredi_karti_ile_ode()   # sayfa: ekrana gel
        chappie.karti_okut()                           # chappie: karti okut
        kart_okutma.kart_okutulmasini_bekle(timeout=30)  # sayfa: ekran kapandi mi

Sayfa nesneleri robottan HABERSIZDIR; yalnizca ekranlari bekler ve gecer.

KOMUTLAR

    chappie.karti_okut()          raftan al + POS'un temassiz alanina okut (NFC)
    chappie.karti_tak()           raftan al + cip okuyucusuna tak
    chappie.pin_gir()             kartin PIN'ini pinpad'den gir ve onayla
    chappie.pin_gir(pin="1234")   belirtilen PIN'i basamak basamak gir
    chappie.karti_yerine_koy()    karti rafa geri koy
    chappie.temizle()             kart nerede olursa olsun rafa dondur

TEZGAH AYARLARI ``chappie/chappie.json`` dosyasindadir (makine, raf, kart, adres,
sureler). Tek seferlik bir kosum icin ortam degiskeniyle ezilebilir:

    ROBOT_MAKINE=1 ROBOT_KART=2 pytest

Oncelik: ortam degiskeni > chappie.json > paketteki varsayilan.

BAGIMLILIKLAR: chappie paketi ``requests``, ``xmltodict``, ``ws4py`` ister.

Chappie neden kimildamiyor:

    python tests/chappie_entegrasyon.py
"""
import logging
import os
import sys

# chappie paketi bu projenin DISINDA, bir ust dizinde duruyor. Iki yol da
# sys.path'e ekleniyor: proje koku (pages/, tests/ importlari icin) ve onun
# ustu (chappie/ importu icin).
_PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UST_DIZIN = os.path.dirname(_PROJE_KOKU)
for _yol in (_PROJE_KOKU, _UST_DIZIN):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

logger = logging.getLogger(__name__)

# chappie paketi MODUL SEVIYESINDE import EDILMEZ: paket burada import edilseydi
# ws4py/xmltodict kurulu olmayan bir makinede robotu hic kullanmayan testler bile
# toplama hatasiyla duserdi. Paket yalnizca baslat() cagrilinca cekilir.

__all__ = ["baslat", "kapat"]


def baslat():
    """Robotu ayaga kaldirir ve komut almaya hazir kolu dondurur.

    Motoru acip RAPID programini baslattigindan saniyeler surer.

    Ayaga kalkamazsa test HATAYLA duser, atlanmaz: chappie kart akisinin
    ayrilmaz parcasi, yoklugu bir tezgah arizasidir.
    """
    from chappie import Chappie, ayarlar

    logger.info("chappie ayağa kaldırılıyor -- %s", ayarlar.ozet())
    return Chappie.baslat(gunluk=logger.info)


def kapat(chappie):
    """Karti rafa koyar, motoru kapatir.

    Kosum dusse de calismasi sart: kart kiskacta unutulursa BIR SONRAKI kosumun
    ilk hareketi raftaki karta carpar. ``durdur(temizlik=True)`` karti (cihazdan
    cikarip) rafa geri koyar.
    """
    chappie.durdur(temizlik=True)


# --------------------------------------------------------------------------------------
# Teshis -- CIHAZA DOKUNMAZ
# --------------------------------------------------------------------------------------
def teshis():
    """Chappie neden kimildamiyor -- adim adim.

    Appium oturumu acmaz, robota komut GONDERMEZ (motoru calistirmaz); yalnizca
    import edilebilirligi ve ag erisimini yoklar.
    """
    print("chappie teşhisi\n" + "=" * 60)

    try:
        import chappie as paket
        from chappie import ayarlar, erisilebilir_mi
        print(f"\n[OK] 1/2 chappie paketi yüklendi (sürüm {paket.SURUM}).")
    except ImportError as hata:
        print(f"\n[X] 1/2 chappie paketi import EDİLEMİYOR:\n    {hata}")
        print("    ÇÖZÜM: paketin bağımlılıklarını kurun:")
        print("        pip install requests xmltodict ws4py")
        return 1

    print(f"yapılandırma : {ayarlar.YAPILANDIRMA_DOSYASI or 'yok (varsayılanlar)'}")
    print(f"ROBOT_HOST   : {ayarlar.ROBOT_HOST}")
    print(f"tezgah       : M{ayarlar.MAKINE} / raf {ayarlar.RAF} / kart {ayarlar.KART}")
    print("=" * 60)

    if not erisilebilir_mi():
        print(f"\n[X] 2/2 Robot denetleyicisine ULAŞILAMIYOR ({ayarlar.ROBOT_HOST}:80).")
        print("    Robot açık mı? Bu PC robotun ağında mı (denetleyiciye doğrudan")
        print("    kablo)? Kontrol: ping " + ayarlar.ROBOT_HOST)
        return 1
    print(f"[OK] 2/2 Robot denetleyicisine ulaşıldı ({ayarlar.ROBOT_HOST}).")

    print("\nSonuç: chappie KULLANILABİLİR -- kart testleri elsiz koşabilir.")
    return 0


if __name__ == "__main__":
    sys.exit(teshis())
