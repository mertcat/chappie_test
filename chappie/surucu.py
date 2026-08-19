"""Robotu süren ana döngü -- ayrı bir process'te koşar.

Kaynağı chappieautomation/devices.py; davranış DEĞİŞTİRİLMEDEN taşındı. Özellikle
iki kazanılmış davranış korundu (ikisi de gerçek tezgahta ayarlanmış):

  * KART_KOY sonrası kuyruğa BAKIP gereksiz raf turunu atlama -- sıradaki komut aynı
    kartı geri alacaksa robot kartı elinde tutar, rafa gidip gelmez.
  * KART_AL_TAK'ı tel üzerinde ÜÇ PARÇA gönderme (komut adı, makine no, kart no).

Robotla üç kanaldan konuşulur:
  1. HTTP REST  motor aç/kapa, program sayacını başa al, programı başlat/durdur
  2. WebSocket  IO sinyallerine abonelik (Job_OK, Gripper_Kart, M<n>_Kartvar)
  3. Ham TCP    komutların gönderildiği kanal; boştayken "0" yazılır (heartbeat)
"""
import json
import logging
import socket
import threading
import time

import requests
import xmltodict
from requests.auth import HTTPDigestAuth
from ws4py.client.threadedclient import WebSocketClient

from chappie import ayarlar, komutlar

logger = logging.getLogger(__name__)

# WebSocket aboneliği kurulamasa bile döngü çalışsın diye varsayılan 1.
# DİKKAT: bu varsayılan yüzünden "abonelik koptu" sessiz kalır -- sinyalleri
# okuyan taraf REST'e düşebilmeli (bkz. chappie.Chappie.sinyal).
_job_ok = 1


class RobotDenetleyici:
    """ABB Robot Web Services üzerinden denetleyiciyi süren REST istemcisi."""

    def __init__(self, host=None):
        self.host = host or ayarlar.ROBOT_HOST
        self.base_url = f"http://{self.host}/"
        self.auth = HTTPDigestAuth(ayarlar.ROBOT_KULLANICI, ayarlar.ROBOT_PAROLA)
        self._calisma_payload = {
            "regain": "continue", "execmode": "continue", "cycle": "once",
            "condition": "none", "stopatbp": "disabled", "alltaskbytsp": "false",
        }

    def _post(self, yol, payload, aciklama):
        cevap = requests.post(self.base_url + yol, data=payload, auth=self.auth,
                              timeout=15)
        # Robot Web Services başarıda gövdesiz 204 döner; başka her şey hatadır.
        if cevap.status_code != 204:
            raise AssertionError(
                f"{aciklama} başarısız -- HTTP {cevap.status_code}: {cevap.text[:200]}")
        logger.info(aciklama)

    def motor_ac(self):
        self._post("rw/panel/ctrlstate?action=setctrlstate",
                   {"ctrl-state": "motoron"}, "motor açıldı")

    def motor_kapat(self):
        self._post("rw/panel/ctrlstate?action=setctrlstate",
                   {"ctrl-state": "motoroff"}, "motor kapatıldı")

    def program_sayacini_sifirla(self):
        self._post("rw/rapid/execution?action=resetpp",
                   {"mastership": "implicit"}, "program sayacı (PP) başa alındı")

    def programi_baslat(self):
        self._post("rw/rapid/execution?action=start", self._calisma_payload,
                   "RAPID programı başlatıldı")

    def programi_durdur(self):
        self._post("rw/rapid/execution?action=stop", self._calisma_payload,
                   "RAPID programı durduruldu")

    def sinyal_oku(self, ad):
        """Bir IO sinyalinin anlık değeri. Cevap XHTML; değer class='lvalue' span'de."""
        cevap = requests.get(f"{self.base_url}rw/iosystem/signals/{ad};state",
                             auth=self.auth, timeout=10)
        spanlar = xmltodict.parse(cevap.text)["html"]["body"]["div"]["ul"]["li"]["span"]
        if isinstance(spanlar, dict):   # tek span dönerse xmltodict listeye sarmaz
            spanlar = [spanlar]
        for span in spanlar:
            if span.get("@class") == "lvalue":
                return int(span.get("#text"))
        raise AssertionError(f"{ad} sinyali okunamadı: {cevap.text[:200]}")

    def guvenli_duruma_al(self):
        """Programı durdurup motoru kapatır. Kapanış yolunda olduğu için hata yutar."""
        for adim, ad in ((self.programi_durdur, "program"), (self.motor_kapat, "motor")):
            try:
                adim()
            except Exception as e:
                logger.warning("Kapatmada %s durdurulamadı: %s", ad, e)


def erisilebilir_mi(host=None, timeout=3):
    """Denetleyicinin web servisi açık mı -- process'i açmadan önce hızlı yoklama."""
    try:
        with socket.create_connection((host or ayarlar.ROBOT_HOST, 80), timeout=timeout):
            return True
    except OSError:
        return False


class _SinyalIstemcisi(WebSocketClient):
    """IO sinyal aboneliği: gelen olayları paylaşılan sözlüğe yazar."""

    def __init__(self, paylasim, location, protocols, headers):
        super().__init__(location, protocols=protocols, headers=headers)
        self.paylasim = paylasim

    def opened(self):
        logger.info("Sinyal aboneliği kuruldu.")

    def closed(self, code, reason=None):
        logger.warning("Sinyal aboneliği kapandı: %s %s", code, reason)

    def received_message(self, olay):
        if not olay.is_text:
            return
        global _job_ok
        try:
            icerik = xmltodict.parse(olay.data.decode("utf-8"))
            li = icerik["html"]["body"]["div"]["ul"]["li"]
            ad = li["@title"]
            if ad in ayarlar.SINYALLER:
                deger = int(li["span"][0]["#text"])
                self.paylasim.io_elements[ad] = deger
                if ad == "Job_OK":
                    _job_ok = deger
        except Exception as e:   # bozuk tek olay döngüyü düşürmemeli
            logger.warning("Sinyal olayı ayrıştırılamadı: %s", e)


def _abonelik_kur(paylasim, host):
    """Sinyal aboneliğini kurar ve olayları dinler (kendi thread'inde koşar)."""
    try:
        payload = {"resources": [str(i + 1) for i in range(len(ayarlar.SINYALLER))]}
        for i, sinyal in enumerate(ayarlar.SINYALLER, start=1):
            payload[str(i)] = f"/rw/iosystem/signals/{sinyal};state"
            payload[f"{i}-p"] = "2"

        oturum = requests.Session()
        cevap = oturum.post(f"http://{host}/subscription",
                            auth=HTTPDigestAuth(ayarlar.ROBOT_KULLANICI,
                                                ayarlar.ROBOT_PAROLA),
                            data=payload)
        cerez = "-http-session-={0}; ABBCX={1}".format(
            cevap.cookies["-http-session-"], cevap.cookies["ABBCX"])
        istemci = _SinyalIstemcisi(paylasim, cevap.headers["Location"],
                                   protocols=["robapi2_subscription"],
                                   headers=[("Cookie", cerez)])
        istemci.connect()
        istemci.run_forever()
    except Exception as e:
        # Abonelik kurulamazsa döngü YİNE ÇALIŞIR (sinyaller REST'ten okunur);
        # bu yüzden hata ölümcül değil ama görünür olmalı.
        logger.warning("Sinyal aboneliği kurulamadı: %s -- sinyaller REST'ten "
                       "okunmaya devam edecek.", e)


def _kart_al_tak_gonder(soket, komut):
    """KART_AL_TAK'ı üç parça halinde yazar: komut adı, makine no, kart no."""
    makine_no = komut.split("M")[1][0]
    kart_no = komut[-1]
    for parca in ("KART_AL_TAK", makine_no, kart_no):
        soket.sendall(parca.encode("utf-8"))
        time.sleep(ayarlar.PARCA_ARASI_ES)


def _kuyruktan_al(paylasim, timeout=5):
    """Kuyrukta komut varsa döndürür, yoksa "0" (boşta) döndürür."""
    try:
        return paylasim.queue_of_commands.get(timeout=timeout)
    except Exception:
        return komutlar.BOSTA


def calistir(paylasim, host=None):
    """Robotu ayağa kaldırır ve terminate_event set edilene kadar komut pompalar.

    Bu fonksiyon AYRI BİR PROCESS'te koşar (bkz. chappie.Chappie.baslat).
    """
    host = host or ayarlar.ROBOT_HOST
    denetleyici = RobotDenetleyici(host)

    abonelik = threading.Thread(target=_abonelik_kur, args=(paylasim, host),
                                daemon=True)
    abonelik.start()

    denetleyici.motor_ac()
    denetleyici.program_sayacini_sifirla()
    denetleyici.programi_baslat()

    soket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soket.settimeout(300)
    soket.connect((host, ayarlar.ROBOT_PORT))
    logger.info("TCP bağlantısı kuruldu (%s:%s)", host, ayarlar.ROBOT_PORT)

    son_komutlar = []
    try:
        while not paylasim.terminate_event.is_set():
            # Robot hazır olmadan yazmak mesajın kaçırılmasına yol açıyor.
            bitis = time.time() + 120
            while not _job_ok and time.time() < bitis:
                time.sleep(0.5)

            komut = _kuyruktan_al(paylasim)

            if "KART_AL_TAK" in komut:
                son_komutlar.append(komut)
                logger.info("gönderiliyor (parçalı): %s", komut)
                _kart_al_tak_gonder(soket, komut)

            elif "KART_KOY" in komut:
                # GEREKSİZ RAF TURUNU ATLA: sıradaki komut AYNI kartı geri alacaksa
                # robot kartı elinde tutabilir; rafa gidip gelmesi boşuna zaman.
                time.sleep(1)
                sonraki = _kuyruktan_al(paylasim)

                ayni_kart_msr = ("MSR" in komut and "MSR" in sonraki
                                 and komut[-5] == sonraki[-5])
                ayni_kart_duz = ("KART_AL" in sonraki and sonraki[-1] == komut[-1]
                                 and "MSR" not in sonraki and "MSR" not in komut)

                if ayni_kart_msr:
                    pass          # ikisi de iptal: kart elde kalır
                elif ayni_kart_duz:
                    if "TAK" in sonraki:
                        makine_no = sonraki.split("M")[1][0]
                        tak = f"KART_TAK_M{makine_no}"
                        son_komutlar.append(tak)
                        logger.info("raf turu atlandı, gönderiliyor: %s", tak)
                        soket.sendall(tak.encode("utf-8"))
                        time.sleep(1)
                else:
                    son_komutlar.append(komut)
                    logger.info("gönderiliyor: %s", komut)
                    soket.sendall(komut.encode("utf-8"))
                    time.sleep(ayarlar.KOMUT_SONRASI_ES)

                    if sonraki != komutlar.BOSTA:
                        son_komutlar.append(sonraki)
                    bitis = time.time() + 120
                    while not _job_ok and time.time() < bitis:
                        time.sleep(0.5)
                    if "KART_AL_TAK" in sonraki:
                        _kart_al_tak_gonder(soket, sonraki)
                    else:
                        soket.sendall(sonraki.encode("utf-8"))
                        time.sleep(ayarlar.KOMUT_SONRASI_ES)

            elif komut == komutlar.BOSTA:
                # Boşta mesajı: RAPID sürekli mesaj beklediği için bu yazım durursa
                # robot komut beklerken asılı kalır. Günlüğü boğmasın diye basılmıyor.
                soket.sendall(komutlar.BOSTA.encode("utf-8"))
                time.sleep(ayarlar.KOMUT_SONRASI_ES)

            else:
                son_komutlar.append(komut)
                logger.info("gönderiliyor: %s", komut)
                soket.sendall(komut.encode("utf-8"))
                time.sleep(ayarlar.KOMUT_SONRASI_ES)

            son_komutlar = son_komutlar[-5:]
        logger.info("Döngüden çıkıldı (terminate_event).")
    finally:
        denetleyici.guvenli_duruma_al()
        try:
            soket.close()
        except Exception:
            pass


def gunluge_calistir(paylasim, gunluk_yolu, paket_yolu=None):
    """calistir()'i çağırır ve TÜM çıktısını ``gunluk_yolu``na yazar.

    Ayrı bir sarmalayıcı gerekiyor çünkü (a) 'spawn' ile açılan process'te hedef
    modül düzeyinde picklable bir fonksiyon olmalı; (b) çocuk process'in çıktısı ve
    hatası aksi halde HİÇBİR YERDE görünmez -- robotun neden kımıldamadığı ancak bu
    günlükten anlaşılır.
    """
    import sys
    if paket_yolu and paket_yolu not in sys.path:
        sys.path.insert(0, paket_yolu)
    with open(gunluk_yolu, "w", encoding="utf-8", buffering=1) as gunluk:
        sys.stdout = gunluk
        sys.stderr = gunluk
        logging.basicConfig(stream=gunluk, level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        try:
            calistir(paylasim)
        except BaseException:
            import traceback
            traceback.print_exc()
            raise
