# chappie_test

Chappie mimarisiyle kurulmus ornek proje. Tek bir test iceriyor: 3500 TL satis, kart NFC ile okutulur, PIN girilir, fis basilir.

Bastan sona elle mudahale gerektirmez.

## Yerlesim

```
chappie_test/
├── chappie/                  <- robotu suren paket (PROJE DISINDA)
│   ├── chappie.json               tezgah ayarlari
│   ├── ayarlar.py                 ayarlari okur
│   ├── chappie.py                 Chappie sinifi -- testlerin kullandigi arayuz
│   ├── komutlar.py                komut dizgilerinin tek kaynagi
│   ├── surucu.py                  robotla konusan dongu (REST + WebSocket + TCP)
│   ├── paylasim.py                process'ler arasi kuyruk + sinyaller
│   └── guvenlik.py                kavrama kontrolleri
│
└── test_projesi/
    ├── main.py                    testi calistirir
    ├── pytest.ini
    ├── config/                    step_count.json -- kosum ozeti buraya yazilir
    ├── run_event/
    │   └── api_logger.py          adimlari API'ye gonderir, ozeti yazar
    ├── pages/                     SADECE LOCATOR -- burada hicbir akis yok
    │   ├── ana_menu.py            Satis sekmesi (Appium oturumu burada aciliyor)
    │   ├── satis.py               satis ekrani
    │   ├── odeme_al.py            odeme yontemi secimi
    │   └── kredi_karti.py         kart okutma, satis tipi, kasiyer no, PIN, fis
    └── tests/
        ├── chappie_entegrasyon.py chappie'nin projeye baglandigi TEK dosya
        ├── conftest.py            driver + chappie fixture'lari
        └── test_3500_tl_kredi_karti.py   AKISIN TAMAMI BURADA
```

Iki kural:

- **`pages/` yalnizca locator tutar.** Metot yok, akis yok, sinif bile yok -- duz modul sabitleri. Bir buton yer degistirdiginde tek satir duzeltilir.
- **Akisin tamami testtedir.** Adimlar yukaridan asagi okunur; ne yapildigini gormek icin baska dosya acmaniz gerekmez.

**`chappie/` proje disinda durur.** Boylece ayni paket birden cok test projesi tarafindan paylasilabilir; her projeye kopyalanmasi gerekmez. `tests/chappie_entegrasyon.py` bir ust dizini `sys.path`e ekleyerek paketi bulur.

## Kim ne yapar

- **`chappie/`** — robotu surer. Karti okutur, PIN'e basar. Bu projeyi, testleri, locator'lari **tanimaz**.
- **`pages/`** — ekranlarin locator'lari, base_page vb. bulunur.
- **`tests/`** — akisin tamami. Hangi adimda robotun ne yapacagina **test karar verir**.
- **`run_event/`** — TX'e gidecek olan logları düzenler 

Arada sarmalayici, yama ya da gizli otomatik davranis yoktur:

```python
assert gorunuyor_mu(driver, kredi_karti.KART_OKUTMA_MESAJI)   # ekran acildi mi
chappie.karti_okut()                                          # chappie: karti okut
assert kaybolmasini_bekle(driver, kredi_karti.KART_OKUTMA_MESAJI, timeout=30)
```

Son satir onemli: **chappie'nin hareketi bitirmesi tek basina "cihaz karti gordu" demek degildir.** Karti gercekten okudugunu ancak ekranin kapanmasindan anlariz.


## Kurulum

```bash
pip install -r test_projesi/requirements.txt
```

`chappie` paketi `requests`, `xmltodict`, `ws4py` ister; ucu de requirements icinde.

## Calistirma

```bash
# 1. Appium sunucusu ayri bir terminalde
appium

# 2. Cihaz takili mi
adb devices

# 3. Robot erisilebilir mi (cihaza dokunmaz, motoru calistirmaz)
cd test_projesi && python tests/chappie_entegrasyon.py

# 4. Test
cd test_projesi && python main.py
```

`main.py` yerine dogrudan pytest de calisir:

```bash
cd test_projesi && pytest
```

## Ayarlar

Robot, kart ve makinelerle ilgili her sey `chappie/chappie.json` dosyasinda. Oncelik:

```
ortam degiskeni   >   chappie/chappie.json   >   paketteki varsayilan
```

Kalici degisiklik icin JSON duzenlenir, tek seferlik kosum icin ortam degiskeniyle ezilir:

```bash
ROBOT_MAKINE=1 ROBOT_KART=2 pytest
```

| Alan | Ortam degiskeni | Varsayilan | Ne ise yarar |
| --- | --- | --- | --- |
| `makine` | `ROBOT_MAKINE` | `3` | Hangi POS cihazi |
| `raf` | `ROBOT_RAF` | `1` | Kartin durdugu raf |
| `kart` | `ROBOT_KART` | `4` | Raftaki kart konumu |
| `robot_host` | `ROBOT_HOST` | `192.168.125.1` | Robot denetleyicisinin adresi |
| `kartlar` | `CHAPPIE_KARTLAR` | 10 kartlik set | Kart numarasi -> PIN |

Tam liste: [chappie/README.md](chappie/README.md)

Cihaz secimi test projesine aittir: tek cihaz takiliysa `adb devices` ciktisindan otomatik bulunur, birden fazlaysa `UDID` ortam degiskeniyle secilir.

## Raporlama

Test adimlari `run_event/api_logger.py` uzerinden kayda geciyor:

```python
from run_event.api_logger import get_api_logger

kayit = get_api_logger()
kayit.log_step_passed("Kart chappie tarafından okutuldu.")
```

Kosum sonunda ozet `config/step_count.json` dosyasina yaziliyor:

```json
{
    "total_steps": 5,
    "start_time": "2026-08-19 10:42:20",
    "end_time": "2026-08-19 10:45:03",
    "duration": "2m 43s",
    "start_battery_level": 87,
    "end_battery_level": 85,
    "run_id": "default_run",
    "agent_id": "local_agent"
}
```

**API zorunlu degildir.** `PUBLIC_BASE_URL` tanimli degilse event gonderimi atlanir; adim sayaci ve ozet yazimi calismaya devam eder. API erisilemezse de test DUSMEZ, yalnizca uyari loglanir -- raporlama bir testi basarisiz kilmamali.

| Ortam degiskeni | Varsayilan | Ne ise yarar |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | — | API adresi; yoksa gonderim atlanir |
| `RUN_ID` | `default_run` | Kosum kimligi |
| `AGENT_ID` | `local_agent` | Agent kimligi |
| `RUNNER_SHARED_SECRET` | — | API kimlik dogrulama basligi |

Batarya seviyesi `adb` ile okunuyor; `adb` yoksa alanlar `null` kalir, logger calismaya devam eder.

Ozet dosyasi **proje kokune** gore yazilir, calisma dizinine gore degil -- `pytest`i nereden calistirirsaniz calistirin ozet hep `test_projesi/config/` altina duser.

## Testin akisi

1. Ana menuden **Satis sekmesine gecilir**
2. `3500` yazilir, ilk kisma tiklanir (sepete kalem eklenir)
3. Devam -> Odeme al -> Kredi K.
4. "Lutfen karti okutun" ekrani beklenir; **chappie karti NFC'ye okutur**
5. Satis Tipi ve Kasiyer No ekranlari **cikarlarsa** gecilir
6. PIN ekrani **cikarsa** **chappie PIN'i girer**
7. Is yeri nushasi yazdirilir, Satis ekranina donulur
8. Kart rafa geri konur (`finally` icinde -- test dusse de calisir)

5. ve 6. adimlarin opsiyonel olmasi kasitlidir: bazi kartlarda akis bu ekranlari atlar, cikmamalari hata degildir.

### Bilinen bir noktadan baslamak

Appium oturumu launcher'in **ana menu** ekraninda aciliyor; rakam tus takimi orada yok. Bu yuzden iki sey yapiliyor:

- **Soguk baslatma** (`conftest.py`): oturum acilir acilmaz ecr / paymentgateway / fiscalservice paketleri kapatilip ana uygulama one aliniyor. `noReset=True` oldugundan cihaz onceki kosumdan kalma bir ekranda (yarim kalmis odeme, acik dialog) durabilir; oradan devam etmek testi ilk adimda dusururdu.
- **Satis sekmesine gecis** (testin 1. adimi): tiklanir ve Satis ekraninin gercekten acildigi dogrulanir. Cihazda ara sira Android'in kendi navigasyon cubugu uygulamanin alt barinin uzerine binip dokunusu yutuyor -- bu durumda bir kez BACK ile temizlenip tekrar deneniyor.

## Yeni test eklemek

`tests/` altina bir dosya acin, `chappie` fixture'ini isteyin ve adimlari dogrudan yazin:

```python
from pages import kredi_karti, odeme_al, satis

def test_yeni_senaryo(driver, chappie):
    for rakam in "100":
        tikla(driver, satis.rakam(rakam))
    driver.find_elements(*satis.KISIM_KARTLARI)[0].click()

    tikla(driver, satis.BTN_DEVAM)
    tikla(driver, odeme_al.BTN_KREDI_KARTI)

    chappie.karti_tak()          # cipe tak -- NFC yerine
    kaybolmasini_bekle(driver, kredi_karti.KART_OKUTMA_MESAJI, timeout=30)
```

Yeni bir ekran gerekiyorsa locator'ini `pages/` altina ekleyin; akisi teste yazin.

Kullanilabilir komutlar `tests/chappie_entegrasyon.py` dosyasinin basinda listelenmistir.

## Sorun giderme

**Robot kimildamiyor** — `python tests/chappie_entegrasyon.py` calistirin. Adimlar sirayla raporlanir; ilk basarisiz adim gercek sebeptir.

**`Queue is empty, sending 0`** — hata **degildir**. Surucunun bosta kalma sinyalidir; robot bostayken saniyede bir yazar ve yazmasi durmamalidir. Anlamli olan, ilk komuttan **sonra** ne yazdigidir.

**Surucu gunlugu** — `chappie_surucu.log`. Surucu process'inin tum ciktisi oraya yazilir; pytest onu yakalamaz.

**Kart kiskacta kaldi** — bir sonraki kosumun ilk hareketi raftaki karta carpar. Test `finally` icinde `chappie.temizle()` cagirir; yine de takildiysa elle alin.
