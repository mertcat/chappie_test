"""Chappie robot tezgahının GLOBAL TANIMLARI -- tek yapılandırma noktası.

Her değer ÜÇ yerden gelebilir; öncelik sırası soldan sağa:

    ortam değişkeni   >   chappie.json   >   buradaki varsayılan

Yani tezgahı kalıcı olarak değiştirmek için ``chappie/chappie.json`` yazarsın, tek
seferlik bir koşum için ortam değişkeniyle ezersin:

    # kalıcı: chappie/chappie.json
    {"makine": 1, "kart": 2}

    # tek seferlik: yalnızca o koşum için
    ROBOT_MAKINE=3 ROBOT_KART=4 pytest ...

``chappie.json`` ARANAN YERLER (ilk bulunan kullanılır):

    1. CHAPPIE_CONFIG ortam değişkeninin gösterdiği dosya (verilmişse ZORUNLU:
       yoksa hata verilir -- yanlış yol sessizce varsayılana düşmesin)
    2. bu paketin içi (chappie/chappie.json) -- normal yer
    3. proje kökü / chappie.json
    4. çalışma dizini / chappie.json

Dosya paketin İÇİNDE durur ki klasörü yeni bir checklist'e kopyaladığında ayarlar
da birlikte gitsin; kopyalayan kişi tek dosyayı düzenleyip tezgahı ayarlar.

Dosya hiç yoksa hata olmaz; her şey varsayılanlarla çalışır. Hangi dosyanın
okunduğunu ``YAPILANDIRMA_DOSYASI`` söyler (teşhis çıktısında da görünür).

Kart PIN'leri de burada: chappieautomation'da bu bilgi ``cards.json``da duruyordu ve
kart numarasından PIN'e çeviren mantık bir behave adımının (robot_steps.py) içine
gömülüydü -- yani koddan komut kuran hiç kimse kullanamıyordu. Pakete taşındı.
"""
import json
import os

SURUM = "1.1.0"

_PAKET_DIZINI = os.path.dirname(os.path.abspath(__file__))
_PROJE_KOKU = os.path.dirname(_PAKET_DIZINI)


def _yapilandirmayi_yukle():
    """chappie.json'u bulup okur. Dönüş: (sözlük, okunan dosyanın yolu ya da None)."""
    acik_yol = os.getenv("CHAPPIE_CONFIG")
    if acik_yol:
        # Açıkça bir yol verilmişse yokluğu HATADIR: yazım hatası yüzünden sessizce
        # varsayılan tezgahla koşmak, yanlış POS'a kart okutmak demek.
        if not os.path.isfile(acik_yol):
            raise FileNotFoundError(
                f"CHAPPIE_CONFIG='{acik_yol}' gösteriyor ama böyle bir dosya yok."
            )
        adaylar = [acik_yol]
    else:
        adaylar = [os.path.join(_PAKET_DIZINI, "chappie.json"),
                   os.path.join(_PROJE_KOKU, "chappie.json"),
                   os.path.join(os.getcwd(), "chappie.json")]

    for aday in adaylar:
        if os.path.isfile(aday):
            with open(aday, encoding="utf-8") as f:
                return json.load(f), aday
    return {}, None


_YAPILANDIRMA, YAPILANDIRMA_DOSYASI = _yapilandirmayi_yukle()


def _deger(anahtar, ortam_degiskeni, varsayilan, tip=str):
    """Bir ayarı öncelik sırasına göre çözer: ortam > chappie.json > varsayılan."""
    ham = os.getenv(ortam_degiskeni)
    if ham is None:
        ham = _YAPILANDIRMA.get(anahtar, varsayilan)
    try:
        return tip(ham)
    except (TypeError, ValueError) as hata:
        nereden = (f"ortam değişkeni {ortam_degiskeni}" if os.getenv(ortam_degiskeni)
                   else f"{YAPILANDIRMA_DOSYASI} içindeki '{anahtar}'")
        raise ValueError(
            f"chappie ayarı okunamadı -- {nereden} = {ham!r}, "
            f"{tip.__name__} bekleniyordu ({hata})."
        ) from hata


# --- Robot denetleyicisi (ABB Robot Web Services) ---
ROBOT_HOST = _deger("robot_host", "ROBOT_HOST", "192.168.125.1")
# RAPID programının komut beklediği ham TCP portu.
ROBOT_PORT = _deger("robot_port", "ROBOT_PORT", 5510, int)
ROBOT_KULLANICI = _deger("robot_kullanici", "ROBOT_KULLANICI", "Default User")
ROBOT_PAROLA = _deger("robot_parola", "ROBOT_PAROLA", "robotics")

# --- Tezgah geometrisi: hangi POS, kart raftaki hangi konumda ---
MAKINE = _deger("makine", "ROBOT_MAKINE", 3, int)
RAF = _deger("raf", "ROBOT_RAF", 1, int)
KART = _deger("kart", "ROBOT_KART", 4, int)

# --- Zamanlamalar ---
# RAPID iki mesajı arka arkaya alırsa ikincisini kaçırıyor; komut sonrası es şart.
KOMUT_SONRASI_ES = _deger("komut_sonrasi_es", "CHAPPIE_KOMUT_ESI", 2, float)
# KART_AL_TAK üç parça halinde gönderilir, parçalar arası daha kısa es yeter.
PARCA_ARASI_ES = _deger("parca_arasi_es", "CHAPPIE_PARCA_ESI", 0.5, float)
# Bir robot hareketinin tamamlanması için tanınan azami süre.
HAREKET_TIMEOUT = _deger("hareket_timeout", "CHAPPIE_HAREKET_TIMEOUT", 180, int)
# devices döngüsünün ayağa kalkıp sinyal vermesi için tanınan süre.
HAZIR_TIMEOUT = _deger("hazir_timeout", "CHAPPIE_HAZIR_TIMEOUT", 30, int)

# --- Robotun çıktısının yazılacağı günlük ---
GUNLUK_DOSYASI = _deger("gunluk_dosyasi", "CHAPPIE_GUNLUK", "chappie_surucu.log")

# --- Abone olunan IO sinyalleri ---
# Job_OK       robot yeni komut alabilir mi
# M<n>_Kartvar cihazda kart var mı
# Gripper_Kart kıskaçta kart var mı
#
# RAPID programında TANIMLI olan sinyallerdir; değiştirmek robot tarafını da
# değiştirmeyi gerektirir. Bu yüzden tek seferlik ortam değişkeniyle ezilmez --
# yalnızca chappie.json ile.
_VARSAYILAN_SINYALLER = ["Job_OK", "Foto_POS", "M1_Kartvar", "M2_Kartvar",
                         "M3_Kartvar", "Gripper_Kart"]
SINYALLER = list(_YAPILANDIRMA.get("sinyaller", _VARSAYILAN_SINYALLER))

# --- Kart no -> PIN ---
_VARSAYILAN_KARTLAR = {
    "2": "1234", "4": "1234", "6": "9999", "8": "9999", "10": "9999",
    "11": "9999", "12": "9999", "13": "9999", "14": "9999", "15": "9999",
}


def _kartlari_yukle():
    """Kart PIN'lerini döndürür.

    Öncelik: CHAPPIE_KARTLAR (ayrı bir JSON dosyası) > chappie.json içindeki
    ``kartlar`` > varsayılan set. CHAPPIE_KARTLAR korunuyor ki birden çok proje
    AYNI kart dosyasını paylaşabilsin.
    """
    yol = os.getenv("CHAPPIE_KARTLAR")
    if yol:
        if not os.path.isfile(yol):
            raise FileNotFoundError(
                f"CHAPPIE_KARTLAR='{yol}' gösteriyor ama böyle bir dosya yok."
            )
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    return dict(_YAPILANDIRMA.get("kartlar", _VARSAYILAN_KARTLAR))


KARTLAR = _kartlari_yukle()


def pin_bul(kart):
    """Kart numarasının PIN'i. Tanımlı değilse tanımlı olanları söyleyerek hata verir."""
    anahtar = str(kart)
    if anahtar not in KARTLAR:
        raise KeyError(
            f"{anahtar} numaralı kartın PIN'i tanımlı değil "
            f"(tanımlı olanlar: {sorted(KARTLAR, key=int)}). "
            "chappie.json içindeki 'kartlar' ile ya da CHAPPIE_KARTLAR ortam "
            "değişkeniyle kendi kart dosyanı verebilirsin."
        )
    return str(KARTLAR[anahtar])


def ozet():
    """Etkin ayarların tek satırlık özeti -- teşhis ve günlük için."""
    kaynak = YAPILANDIRMA_DOSYASI or "yok (varsayılanlar + ortam değişkenleri)"
    return (f"chappie {SURUM} | yapılandırma: {kaynak} | "
            f"robot {ROBOT_HOST}:{ROBOT_PORT} | "
            f"tezgah M{MAKINE} / raf {RAF} / kart {KART}")
