"""Chappie -- testlerin robotla konuştuğu tek arayüz.

    from chappie import Chappie

    kol = Chappie.baslat()
    try:
        kol.karti_okut()          # raftan al + temassız okut (kart eldeyse almaz)
        kol.pin_gir()             # PIN'i pinpad'den gir ve onayla
        kol.karti_yerine_koy()
    finally:
        kol.durdur()

``with Chappie.baslat() as kol:`` de çalışır.

Bu modül pytest'e ya da behave'e BAĞLI DEĞİL: hataları ``ChappieHazirDegil`` /
``TimeoutError`` olarak atar, "atla mı düşür mü" kararını çağırana bırakır.
"""
import logging
import multiprocessing
import os
import time

from chappie import ayarlar, komutlar, surucu
from chappie.guvenlik import KavramaDurumu, dogrula_ve_guncelle
from chappie.paylasim import Paylasim

logger = logging.getLogger(__name__)

PAKET_YOLU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ChappieHazirDegil(Exception):
    """Sürücü ayağa kalkamadı ya da sinyaller okunamıyor."""


class Chappie:

    # Tezgah geometrisi -- alt sınıfta ya da ortam değişkeniyle değiştirilebilir.
    makine, raf, kart = ayarlar.MAKINE, ayarlar.RAF, ayarlar.KART

    def __init__(self, paylasim, surec=None, gunluk_yolu=None, gunluk=None):
        self.paylasim = paylasim
        self.surec = surec
        self.gunluk_yolu = gunluk_yolu
        self.gunluk = gunluk or logger.info
        self.durum = KavramaDurumu()
        self._denetleyici = None       # REST yedeği, ilk ihtiyaçta kurulur

    # ------------------------------------------------------------------ yaşam döngüsü
    @classmethod
    def baslat(cls, gunluk_yolu=None, gunluk=None, hazir_timeout=None):
        """Sürücüyü ayrı process olarak kaldırır ve komut almaya hazır bir kol döndürür."""
        gunluk = gunluk or logger.info
        hazir_timeout = hazir_timeout or ayarlar.HAZIR_TIMEOUT

        if not surucu.erisilebilir_mi():
            raise ChappieHazirDegil(
                f"Robot denetleyicisine ulaşılamıyor ({ayarlar.ROBOT_HOST}:80). "
                "Robot açık mı, bu makine robotun ağında mı?"
            )

        paylasim = Paylasim()
        gunluk_yolu = gunluk_yolu or os.path.abspath(ayarlar.GUNLUK_DOSYASI)
        surec = multiprocessing.Process(
            target=surucu.gunluge_calistir,
            args=(paylasim, gunluk_yolu, PAKET_YOLU),
            name="chappie-surucu",
        )
        surec.start()
        kol = cls(paylasim, surec, gunluk_yolu, gunluk)
        gunluk(f"[chappie] sürücü günlüğü: {gunluk_yolu}")

        # Hazır olmayı sinyal ABONELİĞİNDEN anlamaya çalışmıyoruz: abonelik
        # kurulamasa da sürücü döngüsüne devam eder (Job_OK varsayılanı 1) ve
        # bekleyen taraf sessizce asılı kalırdı. Doğrudan Job_OK OKUNABİLİYOR mu,
        # ona bakılıyor -- gerekirse REST'e düşerek.
        bitis = time.time() + hazir_timeout
        while time.time() < bitis:
            if not surec.is_alive():
                raise ChappieHazirDegil(
                    f"Sürücü ayağa kalkamadı (exitcode={surec.exitcode}).\n"
                    f"--- {gunluk_yolu} (son satırlar) ---\n{kol.gunluk_kuyrugu()}"
                )
            try:
                gunluk(f"[chappie] Job_OK={kol.sinyal('Job_OK')} "
                       f"Gripper_Kart={kol.sinyal('Gripper_Kart')}")
                break
            except Exception as e:
                gunluk(f"[chappie] sinyaller henüz okunamıyor: {e}")
                time.sleep(2)
        else:
            surec.terminate()
            raise ChappieHazirDegil(
                f"Robot sinyalleri {hazir_timeout} sn içinde okunamadı.\n"
                f"--- {gunluk_yolu} (son satırlar) ---\n{kol.gunluk_kuyrugu()}"
            )
        return kol

    def durdur(self, temizlik=True):
        """Kartı yerine koyar, döngüyü sonlandırır, process'i kapatır.

        Sürücü döngüden çıkınca programı durdurup motoru kapatıyor. Koşum düşse de
        çalışması gerektiğinden her adım ayrı korunuyor -- motorun açık kalması
        kabul edilebilir bir sonuç değil.
        """
        if temizlik:
            try:
                self.temizle()
            except Exception as e:
                self.gunluk(f"[chappie] temizlik sırasında hata: {e}")
        try:
            self.paylasim.terminate_event.set()
        except Exception as e:
            self.gunluk(f"[chappie] terminate_event set edilemedi: {e}")
        if self.surec is not None:
            self.surec.join(timeout=60)
            if self.surec.is_alive():
                self.gunluk("[chappie] sürücü kapanmadı, terminate ediliyor")
                self.surec.terminate()
                self.surec.join(timeout=10)
        self.gunluk(f"[chappie] sürücü günlüğü: {self.gunluk_yolu}")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.durdur()

    # ----------------------------------------------------------------------- durum
    def gunluk_kuyrugu(self, satir_sayisi=25):
        """Sürücü process'inin son çıktısı -- hata mesajına iliştirmek için."""
        if not self.gunluk_yolu:
            return "(günlük yok)"
        try:
            with open(self.gunluk_yolu, encoding="utf-8") as f:
                return "".join(f.readlines()[-satir_sayisi:]).strip()
        except OSError:
            return "(günlük okunamadı)"

    def _surucu_yasiyor_mu(self):
        if self.surec is not None and not self.surec.is_alive():
            raise AssertionError(
                f"Sürücü process'i durdu (exitcode={self.surec.exitcode}); robot "
                f"komutları alamıyor.\n--- {self.gunluk_yolu} (son satırlar) ---\n"
                f"{self.gunluk_kuyrugu()}"
            )

    def sinyal(self, ad):
        """IO sinyalinin değeri -- önce paylaşılan sözlük, olmazsa doğrudan REST.

        Aboneliğe bağlanmamasının sebebi: abonelik kurulamazsa sözlük boş kalır ama
        sürücü bunu FARK ETMEZ (kendi Job_OK varsayılanı 1'dir) ve boşta dönmeye
        devam eder. Sinyali yalnızca sözlükten okumak, o durumda çağıranı sessizce
        bekletirdi.
        """
        deger = self.paylasim.sinyal(ad)
        if deger is not None:
            return deger
        if self._denetleyici is None:
            self._denetleyici = surucu.RobotDenetleyici()
        return self._denetleyici.sinyal_oku(ad)

    def kuyruk_boyu(self):
        try:
            return self.paylasim.queue_of_commands.qsize()
        except NotImplementedError:   # bazı platformlarda desteklenmiyor
            return "?"

    # --------------------------------------------------------------------- komutlar
    def gonder(self, komut):
        """Komutu güvenlik kontrollerinden geçirip kuyruğa bırakır."""
        self._surucu_yasiyor_mu()
        dogrula_ve_guncelle(
            self.durum, komut,
            gripper_bekle=lambda: self.sinyal_bekle("Gripper_Kart", 1, timeout=150),
        )
        self.paylasim.queue_of_commands.put(komut, timeout=30)
        # Kuyruk boyunu da yaz: sürücü "boşta" mesajları basmayı sürdürürken buradaki
        # sayı düşmüyorsa komutlar karşı tarafa hiç ulaşmıyor demektir.
        self.gunluk(f"[chappie] kuyruğa kondu: {komut} (kuyruk boyu={self.kuyruk_boyu()})")
        return self

    def kart_al(self, raf=None, kart=None, msr=False):
        return self.gonder(komutlar.kart_al(raf, kart, msr))

    def kart_al_tak(self, makine=None, raf=None, kart=None):
        return self.gonder(komutlar.kart_al_tak(makine, raf, kart))

    def nfc_okut(self, makine=None, poz=1):
        return self.gonder(komutlar.nfc_okut(makine, poz))

    def kart_tak(self, makine=None):
        return self.gonder(komutlar.kart_tak(makine))

    def kart_cikar(self, makine=None):
        return self.gonder(komutlar.kart_cikar(makine))

    def kart_surt(self, makine=None):
        return self.gonder(komutlar.kart_surt(makine))

    def kart_koy(self, raf=None, kart=None, msr=False):
        return self.gonder(komutlar.kart_koy(raf, kart, msr))

    def pinpad(self, makine=None, kart=None, pin=None):
        """PIN'i TEK komutla girer -- yalnızca RAPID'de tanımlı PIN'ler için.

        Tanımlı olmayan bir PIN'de robot sessizce kımıldamaz (bkz.
        komutlar.pinpad). Keyfi PIN için ``pinpad_basamakli`` kullanın.
        """
        return self.gonder(komutlar.pinpad(makine, kart, pin))

    def pinpad_basamakli(self, makine=None, kart=None, pin=None):
        """PIN'i basamak basamak girer ve onaylar -- HERHANGİ bir PIN çalışır.

        Komutlar sırayla kuyruğa bırakılır; sürücü aralarında Job_OK'i bekleyerek
        teker teker gönderir (behave akışlarının basamak başına 2 sn beklemesiyle
        aynı davranış). Tuş vuruşlarının tamamlanmasını beklemek için dönüşte
        ``bekle_bos()`` çağırın.
        """
        for komut in komutlar.pinpad_basamaklari(makine, kart, pin):
            self.gonder(komut)
        return self

    def eve_don(self):
        return self.gonder(komutlar.eve_don())

    # ------------------------------------------------------- hazır akışlar (tezgah)
    def karti_okut(self):
        """Kartı temassız okutur; kıskaç boşsa önce raftan alır.

        KIŞKAÇ DURUMU KONTROL EDİLİYOR: kısmi ödeme, ödeme iptali ve başarısız
        denemenin tekrarı gibi akışlar kartı AYNI koşumda birden çok kez okutuyor.
        Her seferinde koşulsuz kart_al çağırmak, kartı hâlâ tutan robotu rafa geri
        gönderir ve raftaki karta çarptırır.
        """
        if self.durum.gripper_kart:
            self.gunluk(f"[chappie] kart zaten kıskaçta, M{self.makine}'e okutuluyor")
        else:
            self.kart_al(raf=self.raf, kart=self.kart).bekle_bos()
        self.nfc_okut(makine=self.makine).bekle_bos()
        return self

    def karti_tak(self):
        """Kartı çip okuyucusuna takar; kıskaç boşsa önce raftan alır."""
        if not self.durum.gripper_kart:
            self.kart_al(raf=self.raf, kart=self.kart).bekle_bos()
        self.kart_tak(makine=self.makine).bekle_bos()
        return self

    def pin_gir(self, pin=None):
        """Kartın PIN'ini pinpad'den BASAMAK BASAMAK girer ve onaylar.

        Bunun robotla yapılması ZORUNLU: ödeme klavyeleri kart sertifikasyonu gereği
        ENJEKTE edilmiş dokunuşları (Appium click / koordinat) yok sayıyor. Robot
        tuşlara fiziksel bastığı için bu kısıt onu bağlamıyor.

        Basamak basamak biçim kullanılıyor çünkü tek komutluk biçim (``M3_PINPAD_
        1234_OK``) yalnızca RAPID'de AYRICA TANIMLANMIŞ PIN'ler için çalışıyor;
        tanımsız bir PIN'de robot sessizce kımıldamıyor. Rakam prosedürleri her
        PIN için geçerli olduğundan bu yol genel.

        pin: verilmezse ayarlardaki kart numarasının PIN'i kullanılır.
        """
        if pin is None:
            self.pinpad_basamakli(makine=self.makine, kart=self.kart)
        else:
            self.pinpad_basamakli(makine=self.makine, pin=pin)
        return self.bekle_bos()

    def karti_yerine_koy(self):
        """Kıskaçtaki kartı rafa geri koyar; kıskaç boşsa hiçbir şey yapmaz."""
        if not self.durum.gripper_kart:
            self.gunluk("[chappie] kıskaç boş, kart zaten rafında")
            return self
        self.kart_koy(raf=self.raf, kart=self.kart).bekle_bos()
        return self

    def temizle(self):
        """Koşum yarıda kalırsa kartı (cihazdan çıkarıp) rafa geri koyar.

        Kart kıskaçta ya da cihazda unutulursa bir SONRAKİ koşumun ilk hareketi
        raftaki karta çarpar.
        """
        if self.durum.kart_var:
            self.kart_cikar(self.makine).bekle_bos(timeout=60)
        if self.durum.gripper_kart:
            self.kart_koy(self.raf, self.kart,
                          msr=self.durum.msr).bekle_bos(timeout=60)
        return self

    # ---------------------------------------------------------------- senkronizasyon
    def sinyal_bekle(self, ad, deger=1, timeout=150):
        bitis = time.time() + timeout
        while time.time() < bitis:
            if self.sinyal(ad) == deger:
                return self
            time.sleep(0.5)
        raise TimeoutError(f"{ad} sinyali {timeout} sn içinde {deger} olmadı")

    def bekle_bos(self, timeout=None):
        """Kuyruk boşalıp robot yeniden hazır (Job_OK=1) olana kadar bekler.

        Komutlar eşzamansız gittiği için, bir sonraki ekran kontrolünden önce
        hareketin GERÇEKTEN bittiğinden emin olmak gerekiyor.
        """
        timeout = timeout or ayarlar.HAREKET_TIMEOUT
        bitis = time.time() + timeout
        while time.time() < bitis:
            self._surucu_yasiyor_mu()
            if self.paylasim.queue_of_commands.empty() and self.sinyal("Job_OK") == 1:
                time.sleep(1)   # son komut yazıldıktan sonra kısa doğrulama beklemesi
                if (self.paylasim.queue_of_commands.empty()
                        and self.sinyal("Job_OK") == 1):
                    return self
            time.sleep(0.5)
        raise TimeoutError(
            f"Robot {timeout} sn içinde boşa çıkmadı -- kuyruk boş mu: "
            f"{self.paylasim.queue_of_commands.empty()}, "
            f"sinyaller: {dict(self.paylasim.io_elements)}"
        )
