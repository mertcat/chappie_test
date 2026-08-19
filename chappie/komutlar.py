"""Robota gönderilen komut dizgilerinin TEK kaynağı.

Bu sözlük şimdiye kadar hiçbir yerde tanımlı değildi: komutlar ~90 ayrı yerde elle
string olarak yazılıyor (``When command is KART_AL_R1K4``), f-string'lerle kuruluyor
ve ``if "KART_KOY" in input`` gibi substring kontrolleriyle ayrıştırılıyordu. Bir
harf hatası ancak robot boşta beklerken, çalışma anında fark ediliyordu.

Fonksiyonlar yalnızca dizgi üretir -- kuyruğa koymaz, robota göndermez. Böylece
üretilen komut robot olmadan da test edilebilir.
"""
from chappie import ayarlar


def kart_al(raf=None, kart=None, msr=False):
    """Raftan kartı al. msr=True: manyetik şerit kavraması (sürtme için)."""
    raf = ayarlar.RAF if raf is None else raf
    kart = ayarlar.KART if kart is None else kart
    return f"KART_AL_R{raf}K{kart}" + ("_MSR" if msr else "")


def kart_al_tak(makine=None, raf=None, kart=None):
    """Raftan al + cihaza tak, tek komut.

    Ayrı KART_AL + KART_TAK'tan farkı: robot kartı elinde tutup doğrudan cihaza
    gider, raf ile cihaz arasında fazladan tur atmaz. Sürücü bu komutu tel üzerinde
    ÜÇ PARÇA halinde gönderir (bkz. surucu.py) -- dizgi biçimi o ayrıştırmaya bağlı,
    değiştirilirse sürücü de güncellenmeli.
    """
    makine = ayarlar.MAKINE if makine is None else makine
    raf = ayarlar.RAF if raf is None else raf
    kart = ayarlar.KART if kart is None else kart
    return f"KART_AL_TAK_M{makine}_R{raf}K{kart}"


def nfc_okut(makine=None, poz=1):
    """Kıskaçtaki kartı POS'un temassız alanına okut.

    poz: RAPID tarafındaki okutma varyantı (mevcut akışlarda 1 ve 3 kullanılıyor).
    """
    makine = ayarlar.MAKINE if makine is None else makine
    return f"KART_NFC_M{makine}_{poz}"


def kart_tak(makine=None):
    """Kartı POS'un çip okuyucusuna tak."""
    return f"KART_TAK_M{ayarlar.MAKINE if makine is None else makine}"


def kart_cikar(makine=None):
    """Kartı çip okuyucusundan çıkar."""
    return f"KART_CIKAR_M{ayarlar.MAKINE if makine is None else makine}"


def kart_surt(makine=None):
    """Kartı manyetik şerit okuyucusundan geçir (MSR kavraması gerektirir)."""
    return f"KART_MS_M{ayarlar.MAKINE if makine is None else makine}"


def kart_koy(raf=None, kart=None, msr=False):
    """Kartı rafa geri koy."""
    raf = ayarlar.RAF if raf is None else raf
    kart = ayarlar.KART if kart is None else kart
    return f"KART_KOY_R{raf}K{kart}" + ("_MSR" if msr else "")


def _pin_coz(kart, pin):
    if (kart is None) == (pin is None):
        raise ValueError("'kart' ya da 'pin'den tam olarak biri verilmeli")
    return str(pin) if pin is not None else ayarlar.pin_bul(kart)


def pinpad(makine=None, kart=None, pin=None):
    """PIN'in TAMAMINI tek komutta gir ve onayla: ``M3_PINPAD_1234_OK``.

    DİKKAT -- BU BİÇİM HER PIN İÇİN ÇALIŞMAZ. Robot tarafındaki RAPID programında
    her PIN için AYRI BİR PROSEDÜR tanımlı; komut kayıtlı prosedürlerden birine
    denk gelmiyorsa robot HİÇ KIMILDAMAZ ve hata da vermez (gerçek tezgahta
    ölçüldü: ``M3_PINPAD_3434_OK`` kayıtlı olmadığı için sessizce yok sayıldı).

    Yalnızca RAPID'de tanımlı olduğunu BİLDİĞİN PIN'ler için kullan; keyfi bir PIN
    girecekseniz ``pinpad_basamaklari`` kullanın.
    """
    makine = ayarlar.MAKINE if makine is None else makine
    return f"M{makine}_PINPAD_{_pin_coz(kart, pin)}_OK"


def pinpad_basamaklari(makine=None, kart=None, pin=None):
    """PIN'i basamak basamak giren komut LİSTESİ döndürür.

    ``3434`` için: ``[M3_PINPAD_3, M3_PINPAD_4, M3_PINPAD_3, M3_PINPAD_4,
    M3_PINPAD_OK]``

    ``pinpad``ten farkı: RAPID'de her RAKAM için bir prosedür var (tuşa bas), her
    PIN için ayrı prosedür gerekmiyor -- bu yüzden HERHANGİ BİR PIN girilebilir.
    Bu biçim CommonSteps.py'deki çip ödeme akışında da kullanılıyor.

    Dönüş bir LİSTEDİR; komutlar sırayla kuyruğa bırakılmalı (bkz.
    Chappie.pinpad_basamakli).
    """
    makine = ayarlar.MAKINE if makine is None else makine
    cozulen = _pin_coz(kart, pin)
    if not cozulen.isdigit():
        raise ValueError(f"PIN yalnızca rakamlardan oluşmalı: {cozulen!r}")
    return [f"M{makine}_PINPAD_{basamak}" for basamak in cozulen] + [
        f"M{makine}_PINPAD_OK"
    ]


def eve_don():
    """Kolu başlangıç pozisyonuna al."""
    return "HOMING"


# Robot boştayken sokete yazılan "iş yok" mesajı. RAPID sürekli mesaj beklediği için
# bu yazım durursa robot komut beklerken asılı kalır.
BOSTA = "0"
