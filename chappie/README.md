# chappie

ABB robot koluyla POS cihazına kart okutan test paketi. Kredi kartı ödemesi gerektiren
otomasyon testlerinde kartın fiziksel olarak okutulması ve PIN'in girilmesi, testin
kendi başına yapamayacağı adımlardır; bu paket o iki adımı robota devreder.

**Kendi kendine yeter.** Robotu süren döngü de içinde olduğu için başka bir projeye
bağımlı değildir — klasörü olduğu gibi herhangi bir checklist projesine kopyalayıp
kullanabilirsin.

    chappie/
    ├── __init__.py     açık API
    ├── chappie.json    TEZGAH AYARLARI -- kopyaladıktan sonra düzenlenecek tek dosya
    ├── ayarlar.py      ayarları okur (chappie.json + ortam değişkeni + varsayılan)
    ├── komutlar.py     komut dizgilerinin tek kaynağı
    ├── guvenlik.py     kavrama kontrolleri (robotu kendinden korur)
    ├── paylasim.py     process'ler arası kuyruk + sinyaller
    ├── surucu.py       robotla konuşan döngü (REST + WebSocket + TCP)
    └── chappie.py      Chappie — testlerin kullandığı arayüz

---

## Kurulum

```bash
# 1. klasörü proje köküne kopyala
cp -r /yol/chappie /yeni/checklist/

# 2. bağımlılıklar
pip install requests xmltodict ws4py

# 3. tezgahı ayarla -- makine/raf/kart numaraları
$EDITOR /yeni/checklist/chappie/chappie.json
```

Standart kütüphane dışında yalnızca bu üçü gerekiyor.

**Gereken ortam:** testi koşan makine robot denetleyicisinin ağında olmalı
(varsayılan `192.168.125.1`; denetleyiciye genelde doğrudan kabloyla bağlanılır).

---

## Hızlı başlangıç

```python
from chappie import Chappie

with Chappie.baslat() as chappie:
    chappie.karti_okut()          # raftan al + temassız okut
    chappie.pin_gir()             # PIN'i pinpad'den gir ve onayla
    chappie.karti_yerine_koy()    # kartı rafa geri koy
```

`with` bloğundan çıkarken kart yerine konur, RAPID programı durur, motor kapanır —
test düşse bile.

Elle yönetmek istersen:

```python
chappie = Chappie.baslat()
try:
    chappie.karti_okut()
finally:
    chappie.durdur(temizlik=True)
```

---

## Nasıl çalışıyor: iki process, arada bir kuyruk

Robot **eşzamansız**dır: komut gönderirsin, hareket saniyeler sürer. Ayrıca RAPID
programı sürekli mesaj bekler — kuyruk boşken bile ona "iş yok" (`"0"`) yazmak gerekir,
yoksa robot komut beklerken asılı kalır. Bu yüzden robotu süren kod ayrı bir process'te
kesintisiz döner:

```
  TEST PROCESS                              SÜRÜCÜ PROCESS
  (pytest)                                  (chappie-surucu)
  ┌──────────────────┐                      ┌────────────────────────┐
  │ chappie.py       │   queue_of_commands  │ surucu.py              │
  │   Chappie        │ ───────────────────► │  sonsuz döngü          │
  │                  │                      │   ├─ REST   motor/PP   │
  │ komutlar.py      │   io_elements        │   ├─ WS     sinyaller  │ ──► ROBOT
  │ guvenlik.py      │ ◄─────────────────── │   └─ TCP    komutlar   │
  └──────────────────┘                      └────────────────────────┘
                          paylasim.py
```

`Chappie.baslat()` sürücü process'ini ayağa kaldırır: motoru açar, program sayacını
(PP) başa alır, RAPID programını başlatır, sinyal aboneliğini kurar.

---

## Üç katman: `komutlar` vs `Chappie`

İki dosyada aynı isimler var; farkları önemli.

### 1. `komutlar.py` — sadece metin üretir

```python
komutlar.kart_al(1, 4)        # → "KART_AL_R1K4"
komutlar.pinpad(1, kart=4)    # → "M1_PINPAD_1234_OK"
```

Saf fonksiyon: yan etkisi yok, robot gerekmez, kuyruğa bir şey koymaz. Bu yüzden komut
sözlüğünün doğruluğu robot olmadan test edilebilir.

*Neden ayrı dosya:* bu dizgiler eskiden ~90 ayrı yerde elle yazılıyordu
(`When command is KART_AL_R1K4`). Bir harf hatası ancak robot boşta beklerken, çalışma
anında fark ediliyordu.

### 2. `chappie.py` komut metotları — üretir **ve gönderir**

```python
chappie.kart_al(1, 4)
```

```python
def kart_al(self, raf=None, kart=None, msr=False):
    return self.gonder(komutlar.kart_al(raf, kart, msr))   # 1. dizgiyi üret

def gonder(self, komut):
    self._surucu_yasiyor_mu()                              # 2. sürücü yaşıyor mu
    dogrula_ve_guncelle(self.durum, komut, ...)            # 3. güvenlik + durum
    self.paylasim.queue_of_commands.put(komut)             # 4. kuyruğa bırak
```

`komutlar.kart_al` **ne yapılacağını** söyler, `chappie.kart_al` **yaptırır**.

### 3. `chappie.py` hazır akışlar — birden çok komutu zincirler

```python
chappie.karti_okut()          # kıskaç boşsa kart_al + bekle_bos, sonra nfc_okut + bekle_bos
chappie.karti_tak()           # kıskaç boşsa kart_al + bekle_bos, sonra kart_tak + bekle_bos
chappie.pin_gir()             # pinpad + bekle_bos
chappie.karti_yerine_koy()    # kıskaç doluysa kart_koy + bekle_bos, boşsa hiçbir şey
```

Tezgah geometrisini (`MAKINE/RAF/KART`) ayarlardan bilirler ve hareketin bitmesini
beklerler. Testlerin kullanması gereken katman budur — hangi raftan hangi kartın
alındığını bilmeleri gerekmez.

| Katman | Örnek | Ne yapar | Robot lazım mı |
|---|---|---|---|
| dizgi | `komutlar.kart_al(1,4)` | `"KART_AL_R1K4"` döner | hayır |
| komut | `chappie.kart_al(1,4)` | üretir + doğrular + kuyruğa koyar | evet |
| akış | `chappie.karti_okut()` | al + okut + bitişini bekler | evet |

---

## Komut sözlüğü

| `chappie` metodu | Üretilen komut |
|---|---|
| `kart_al(raf, kart, msr=False)` | `KART_AL_R1K4` / `KART_AL_R1K4_MSR` |
| `kart_al_tak(makine, raf, kart)` | `KART_AL_TAK_M1_R1K4` |
| `nfc_okut(makine, poz=1)` | `KART_NFC_M1_1` |
| `kart_tak(makine)` | `KART_TAK_M1` |
| `kart_surt(makine)` | `KART_MS_M1` |
| `pinpad(makine, kart=…)` | `M1_PINPAD_1234_OK` (PIN ayarlardan) |
| `pinpad(makine, pin="1111")` | `M1_PINPAD_1111_OK` |
| `kart_cikar(makine)` | `KART_CIKAR_M1` |
| `kart_koy(raf, kart, msr=False)` | `KART_KOY_R1K4` / `KART_KOY_R1K4_MSR` |
| `eve_don()` | `HOMING` |
| `gonder("...")` | ham komut (kaçış yolu) |

Parametreler verilmezse `ayarlar.py`'deki tezgah varsayılanları kullanılır.

### Tipik akışlar

```python
# Temassız (NFC)
chappie.kart_al().bekle_bos()
chappie.nfc_okut().bekle_bos()
chappie.kart_koy().bekle_bos()

# Çip + PIN
chappie.kart_al_tak().bekle_bos()
chappie.pinpad(kart=4).bekle_bos()
chappie.kart_cikar().bekle_bos()
chappie.kart_koy().bekle_bos()

# Manyetik şerit
chappie.kart_al(msr=True).bekle_bos()
chappie.kart_surt().bekle_bos()
chappie.kart_koy(msr=True).bekle_bos()
```

---

## Senkronizasyon: `bekle_bos()`

Komutlar kuyruğa **eşzamansız** bırakılır. Bir sonraki ekran kontrolüne geçmeden önce
robotun hareketi gerçekten bitirdiğinden emin olmak gerekir:

```python
chappie.nfc_okut().bekle_bos()   # kuyruk boşalana VE Job_OK=1 olana kadar bekler
```

`bekle_bos()` her turda sürücü process'inin yaşadığını da kontrol eder — sürücü ölürse
dakikalarca sessizce beklemek yerine gerekçesiyle düşer. Zaman aşımında kuyruk durumunu
ve son sinyal değerlerini mesaja yazar.

---

## Güvenlik katmanı (`guvenlik.py`)

Kıskacın durumunu (`msr`, `kart_var`, `gripper_kart`) izleyen küçük bir durum makinesi.
Komut kuyruğa **girmeden önce** dört ihlali reddeder:

| İhlal | Neden |
|---|---|
| MSR kavramasıyla tutulan kartı çipe sokmak | kart da okuyucu da zarar görür |
| Normal kavramayla tutulan kartı şeritten geçirmek | sürtme MSR kavraması gerektirir |
| Yanlış kavramayla rafa koymak | kartı ve rafı hasarlar |
| Boş kıskaçla rafa gitmek | raftaki kartı devirir (`Gripper_Kart` sinyali beklenir) |

İhlalde `KavramaHatasi` atar ve akışı durdurur — sessizce düzeltmeye çalışmaz, çünkü
yanlış varsayımla hareket etmek daha tehlikelidir.

`karti_okut()` ayrıca kartın zaten elde olup olmadığına bakar: kısmi ödeme, ödeme iptali
ve başarısız denemenin tekrarı gibi akışlar kartı aynı koşumda birden çok kez okutur;
her seferinde koşulsuz `kart_al` çağırmak, kartı hâlâ tutan robotu rafa geri gönderip
raftaki karta çarptırırdı.

---

## Ayarlar

Tezgahla ilgili her şey `chappie.json`de — paketin İÇİNDE, yanı başında. Klasörü yeni
bir checklist'e kopyaladığında ayarlar da birlikte gider; kopyalayan kişi tek dosyayı
düzenleyip tezgahı ayarlar.

Bir ayar üç yerden gelebilir, öncelik soldan sağa:

```
ortam değişkeni   >   chappie.json   >   ayarlar.py'deki varsayılan
```

Kalıcı değişiklik JSON'a yazılır, tek seferlik koşum ortam değişkeniyle ezilir:

```bash
ROBOT_MAKINE=1 ROBOT_KART=2 pytest tests/
```

```json
{
  "makine": 3,
  "raf": 1,
  "kart": 4,
  "robot_host": "192.168.125.1",
  "kartlar": { "4": "1234", "6": "9999" }
}
```

| Alan | Ortam değişkeni | Varsayılan | Ne |
|---|---|---|---|
| `makine` | `ROBOT_MAKINE` | `3` | kartın okutulacağı POS (M1/M2/M3) |
| `raf` / `kart` | `ROBOT_RAF` / `ROBOT_KART` | `1` / `4` | kartın raftaki konumu |
| `robot_host` | `ROBOT_HOST` | `192.168.125.1` | denetleyici adresi |
| `robot_port` | `ROBOT_PORT` | `5510` | RAPID'in komut beklediği TCP portu |
| `robot_kullanici` / `robot_parola` | `ROBOT_KULLANICI` / `ROBOT_PAROLA` | `Default User` / `robotics` | digest kimlik |
| `komut_sonrasi_es` | `CHAPPIE_KOMUT_ESI` | `2` sn | komut sonrası es (RAPID mesajı kaçırmasın) |
| `parca_arasi_es` | `CHAPPIE_PARCA_ESI` | `0.5` sn | `KART_AL_TAK` parçaları arası es |
| `hareket_timeout` | `CHAPPIE_HAREKET_TIMEOUT` | `180` sn | `bekle_bos` üst sınırı |
| `hazir_timeout` | `CHAPPIE_HAZIR_TIMEOUT` | `30` sn | sürücünün ayağa kalkması için tanınan süre |
| `gunluk_dosyasi` | `CHAPPIE_GUNLUK` | `chappie_surucu.log` | sürücünün çıktı dosyası |
| `kartlar` | `CHAPPIE_KARTLAR` | 10 kartlık set | kart→PIN eşlemesi |
| `sinyaller` | — | 6 sinyal | abone olunan IO sinyalleri |

`sinyaller` RAPID'de tanımlı olanlardır; değiştirmek robot tarafını da değiştirmeyi
gerektirdiğinden tek seferlik ortam değişkeniyle ezilmez.

**Dosya arama sırası** (ilk bulunan kullanılır): `CHAPPIE_CONFIG`'in gösterdiği dosya →
`chappie/chappie.json` → proje kökü → çalışma dizini. Hiç yoksa hata olmaz,
varsayılanlarla çalışır. `CHAPPIE_CONFIG` verildiyse dosyanın var olması ZORUNLUDUR:
yazım hatası yüzünden sessizce varsayılan tezgahla koşmak, yanlış POS'a kart okutmak
demektir.

```bash
# birden fazla tezgah
CHAPPIE_CONFIG=tezgahlar/tezgah_2.json pytest
```

Etkin ayarların özeti: `python -c "from chappie import ayarlar; print(ayarlar.ozet())"`

Kart PIN'leri `kartlar` alanında tutulur. Birden çok proje AYNI kart setini
paylaşacaksa `CHAPPIE_KARTLAR` ile ortak bir dosya gösterilebilir:

```bash
CHAPPIE_KARTLAR=/ortak/kartlar.json pytest ...
```

---

## Yeni bir checklist'e bağlama

Paket ile projenin arasındaki bağ **tek bir dosyada** tutulur:
`tests/chappie_entegrasyon.py`. Sayfa nesneleri chappie'den habersizdir; komutu her
zaman TEST tarafı verir. Arada sarmalayıcı, yama ya da gizli otomatik davranış yoktur.

### 1. pytest fixture

```python
# tests/chappie_entegrasyon.py
import logging, pytest

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def chappie():
    # Paket MODÜL SEVİYESİNDE import EDİLMEZ: bu dosyayı conftest çekiyor, ws4py
    # kurulu olmayan makinede robotu kullanmayan testler de düşerdi.
    from chappie import Chappie, ayarlar

    logger.info("chappie ayağa kaldırılıyor -- %s", ayarlar.ozet())
    chappie = Chappie.baslat(gunluk=logger.info)

    yield chappie

    # Koşum düşse de motor açık kalmasın, kart kıskaçta unutulmasın.
    chappie.durdur(temizlik=True)
```

`scope="session"`: ayağa kaldırmak motoru açıp RAPID programını başlattığından
saniyeler sürer; her testte tekrarlanması hem yavaş hem gereksiz. Fixture'ı istemeyen
testler robotu hiç çalıştırmaz.

Ayağa kalkamazsa test **hatayla düşer**, atlanmaz — robot artık kart akışının ayrılmaz
parçası, yokluğu bir tezgah arızasıdır.

### 2. conftest.py'ye bağla

```python
# tests/conftest.py
from tests.chappie_entegrasyon import chappie  # noqa: F401
```

> Bunu `pytest.ini` içinde `-p tests.chappie_entegrasyon` ile eklenti olarak
> yüklemeye çalışma. `-p` eklentileri conftest toplanmasından ÖNCE yüklenir; o anda
> proje kökü `sys.path`te olmadığından `pytest` konsol betiğiyle koşarken
> "No module named 'tests'" hatası verir. (`python -m pytest` çalışma dizinini
> `sys.path`e eklediği için hatayı maskeler — iki biçimle de dene.)

### 3. Testte kullan

**Adım adım sürme** — yeni test yazarken bu biçim. Sayfa nesneleri ekranları bekler ve
geçer, chappie hareketi yapar:

```python
def test_kart_takarak_ode(driver, chappie):
    kart_okutma = odeme_al.kredi_karti_ile_ode()
    assert kart_okutma.gorunuyor_mu()

    chappie.karti_tak()                  # ya da karti_okut() -- NFC
    assert kart_okutma.kart_okutulmasini_bekle(timeout=30)

    pin_girisi = PinGirisiPage(driver)
    if pin_girisi.gorunuyor_mu():
        chappie.pin_gir(pin="3434")
        assert pin_girisi.elle_girilmesini_bekle(timeout=30)
```

**Paketlenmiş akış** — proje kart ödemesinin tamamını süren bir sayfa metoduna
sahipse (kart okutma → Satış Tipi → Kasiyer No → PIN → İş yeri nüshası, üstüne
bağlantı hatasında yeniden deneme), chappie'yi düz bir argüman olarak geçir. Komutlar
akışın içinde, ekranın gerçekten açıldığı anda verilir:

```python
def test_kredi_karti_ile_satis(driver, chappie):
    odeme_al.kredi_karti_ile_ode_tam_akis(kasiyer_no="1", chappie=chappie)
```

Sayfa tarafında yapılacak tek şey, beklemeden hemen ÖNCE komutu vermek:

```python
chappie.karti_okut()
kart_okutma.kart_okutulmasini_bekle(timeout=kart_bekleme_suresi)
```

Hangi biçimi kullanırsan kullan şunu unutma: **robotun hareketi tamamlaması TEK BAŞINA
"cihaz kartı gördü" demek değildir.** Ekranın gerçekten kapandığını doğrulayan sayfa
mantığı her zaman çalışmalıdır.

---

## Teşhis: robot neden kımıldamıyor

Belirti çoğunlukla aynıdır — "robot hareket etmedi" — ama sebep birkaç farklı yerde
olabilir. Sırayla kontrol et:

**1. Paket, bağımlılıkları ve etkin ayarlar**
```python
from chappie import ayarlar; print(ayarlar.ozet())
```
`ModuleNotFoundError` → `pip install requests xmltodict ws4py`

Çıktı hangi `chappie.json`un okunduğunu ve hangi tezgahın etkin olduğunu söyler --
robot kımıldıyor ama yanlış POS'a gidiyorsa ilk bakılacak yer burasıdır.

**2. Ağ**
```python
from chappie import erisilebilir_mi; print(erisilebilir_mi())
```
`False` → bu makine robotun ağında değil (`ping 192.168.125.1`). Sürücü bu durumda
`motor_on()`da `ConnectionError` ile ölür.

**3. Sürücü günlüğü** — `chappie_surucu.log`

Sürücü process'inin tüm çıktısı ve hatası buraya yazılır; pytest onu yakalamaz.
`Chappie` hata mesajlarına bu dosyanın son satırlarını kendisi iliştirir.

> **`Queue is empty, sending 0` bir hata DEĞİLDİR.** Bu, sürücünün boşta kalma
> sinyalidir — kuyrukta komut yokken robota saniyede bir "iş yok" yazar. RAPID sürekli
> mesaj beklediği için bu yazım durmamalıdır. Testin UI adımları sürerken bu satırların
> yüzlercesi birikir; normaldir. Anlamlı olan, ilk komuttan **sonra** ne yazdığıdır.

**4. Komutlar karşıya geçiyor mu**

Her `gonder()` çağrısı kuyruk boyunu da yazar:
```
[chappie] kuyruğa kondu: KART_AL_R1K4 (kuyruk boyu=0)
```
Sürücü boşta mesajları basmayı sürdürürken buradaki sayı düşmüyorsa komutlar karşı
tarafa hiç ulaşmıyor demektir.

**5. Sinyal aboneliği**

WebSocket aboneliği kurulamazsa `io_elements` boş kalır, ama sürücü bunu **fark etmez**
(kendi `Job_OK` varsayılanı `1`) ve boşta dönmeye devam eder. Bu yüzden `chappie.sinyal()`
sözlükte değer bulamazsa **REST'ten doğrudan okur**. Abonelik kurulamadıysa günlükte
uyarı vardır; koşum yine de çalışır, yalnızca sinyal okuması yavaşlar.

---

## Bilinen sınırlar

- **QR / yemek kartı ödemeleri otomatikleştirilemez.** Robot bir kart tutucudur; QR
  müşterinin telefon ekranından okutulur.
- **PIN yalnızca robotla girilebilir.** Ödeme klavyeleri kart sertifikasyonu gereği
  enjekte edilmiş dokunuşları (Appium click / koordinat) yok sayar. Robot tuşlara
  fiziksel bastığı için bu kısıt onu bağlamaz.
- **`spawn` tuzağı (macOS/Windows).** Çocuk process modülü yeniden import eder; modül
  düzeyindeki kod tekrar çalışır. Robotu kullanan kodu `if __name__ == "__main__":`
  altına ya da bir fonksiyona koy. pytest fixture'larında sorun çıkmaz.
- **Kopyalar ayrışır.** Paket kopyala-yapıştır ile dağıtıldığından bir düzeltme diğer
  kopyalara kendiliğinden gitmez. `ayarlar.SURUM` bunun içindir: bir kopyayı
  düzelttiğinde sürümü artır ve diğerlerine yay.

---

## API özeti

```python
from chappie import Chappie, ChappieHazirDegil, erisilebilir_mi, KavramaHatasi, SURUM
```

**Yaşam döngüsü**
`Chappie.baslat(gunluk_yolu=None, gunluk=None, hazir_timeout=None)` ·
`durdur(temizlik=True)` · `temizle()` · `with` desteği

**Komutlar**
`kart_al` · `kart_al_tak` · `nfc_okut` · `kart_tak` · `kart_surt` · `pinpad` ·
`kart_cikar` · `kart_koy` · `eve_don` · `gonder`

**Hazır akışlar**
`karti_okut()` · `karti_tak()` · `pin_gir(pin=None)` · `karti_yerine_koy()` · `temizle()`

**Ayarlar**
`ayarlar.ozet()` · `ayarlar.YAPILANDIRMA_DOSYASI` · `ayarlar.pin_bul(kart)`

**Durum / senkronizasyon**
`bekle_bos(timeout=None)` · `sinyal(ad)` · `sinyal_bekle(ad, deger=1, timeout=150)` ·
`kuyruk_boyu()` · `gunluk_kuyrugu(satir_sayisi=25)`

**Hatalar**
`ChappieHazirDegil` (sürücü ayağa kalkamadı / sinyaller okunamıyor) ·
`KavramaHatasi` (komut kıskaç durumuyla bağdaşmıyor) ·
`TimeoutError` (`bekle_bos` / `sinyal_bekle` süre aşımı)

---

Sürüm 1.1.0
