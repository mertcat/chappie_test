"""Kavrama güvenlik kontrolleri -- robotu kendinden korur.

Kaynağı chappieautomation/pusher.py; mantık DEĞİŞTİRİLMEDEN taşındı, yalnızca
behave'in ``context`` nesnesine bağımlılığı kaldırıldı (artık herhangi bir durum
nesnesiyle çalışır).

NEDEN VAR: robota gönderilen komutlar tek başına anlamlı görünse de sıraları
yanlışsa donanıma zarar verir --

  * MSR (manyetik şerit) kavramasıyla tutulan kartı çip okuyucusuna sokmak
  * normal kavramayla tutulan kartı şeritten geçirmeye çalışmak
  * boş kıskaçla rafa gitmek (raftaki kartı devirir)
  * kartı yanlış kavramayla rafa koymak

Bu kontroller komut kuyruğa GİRMEDEN önce çalışır ve ihlalde akışı durdurur;
sessizce düzeltmeye çalışmazlar, çünkü yanlış varsayımla devam etmek daha tehlikeli.
"""


class KavramaHatasi(AssertionError):
    """Komut, kıskacın o anki durumuyla bağdaşmıyor -- hareket ettirilirse hasar riski."""


class KavramaDurumu:
    """Kıskacın izlenen durumu: kart elde mi, hangi kavramayla, cihazda kart var mı.

    behave tarafında bu üç bayrak ``context`` üzerinde tutuluyordu (environment.py
    before_scenario) -- aynı anlamlar korundu.
    """

    def __init__(self):
        self.msr = False           # eldeki kart MSR kavramasıyla mı tutuluyor
        self.kart_var = False      # cihazın (POS) içinde kart var mı
        self.gripper_kart = False  # kıskaçta kart var mı

    def __repr__(self):
        return (f"KavramaDurumu(msr={self.msr}, kart_var={self.kart_var}, "
                f"gripper_kart={self.gripper_kart})")


def dogrula_ve_guncelle(durum, komut, gripper_bekle=None):
    """Komutu kavrama durumuna göre doğrular ve durumu günceller.

    gripper_bekle: KART_KOY öncesi ``Gripper_Kart`` sinyalinin gerçekten 1 olmasını
    bekleyen callable (sürücü tarafından verilir). Verilmezse yalnızca yerel durum
    kullanılır -- sinyal doğrulaması yapılmaz.

    İhlalde KavramaHatasi fırlatır; komut kuyruğa KONMAZ.
    """
    if "KART_KOY" in komut:
        msr_komutu = "MSR" in komut
        if msr_komutu != durum.msr:
            raise KavramaHatasi(
                f"'{komut}' rafa koyma komutu kavramayla uyuşmuyor: kart "
                f"{'MSR' if durum.msr else 'normal'} kavramayla tutuluyor ama komut "
                f"{'MSR' if msr_komutu else 'normal'} kavrama istiyor. "
                "Yanlış kavramayla rafa koymak kartı ve rafı hasarlar."
            )
        if gripper_bekle is not None:
            gripper_bekle()
        durum.gripper_kart = False
        durum.msr = False

    if "KART_AL" in komut:
        durum.gripper_kart = True
        if "MSR" in komut:
            durum.msr = True

    if "TAK" in komut:
        if durum.msr:
            raise KavramaHatasi(
                f"'{komut}': MSR kavramasıyla tutulan kart çip okuyucusuna "
                "sokulamaz -- kart da okuyucu da zarar görür."
            )
        durum.kart_var = True
        durum.gripper_kart = False

    if "KART_CIKAR" in komut:
        durum.kart_var = False
        durum.gripper_kart = True
        durum.msr = False

    if "_MS_" in komut and not durum.msr:
        raise KavramaHatasi(
            f"'{komut}': normal kavramayla tutulan kart manyetik şeritten "
            "geçirilemez -- şerit okuyucuya sürtme MSR kavraması gerektirir."
        )

    return durum
