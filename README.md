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
└── test_projesi/             <- test projesi
    ├── main.py                    testi calistirir
    ├── pytest.ini
    ├── pages/                     ekranlar
    │   ├── base_page.py           tum sayfalarin atasi (Appium ile konusan tek yer)
    │   ├── driver_setup.py        Appium oturumu
    │   ├── satis_page.py          tutar gir, kisim sec, Devam
    │   ├── odeme_al_page.py       Kredi K. sec
    │   └── kredi_karti/
    │       ├── grup_kapama_page.py      bankanin opsiyonel onayi
    │       ├── kart_okutma_page.py      "Lutfen karti okutun"
    │       ├── satis_tipi_page.py       Satis / Taksitli  (opsiyonel)
    │       ├── kasiyer_no_page.py       Kasiyer No        (opsiyonel)
    │       ├── pin_girisi_page.py       "PIN girisi bekleniyor" (opsiyonel)
    │       └── is_yeri_nushasi_page.py  fis yazdirma
    └── tests/
        ├── chappie_entegrasyon.py  chappie'nin projeye baglandigi TEK dosya
        ├── conftest.py             driver + chappie fixture'lari
        └── test_3500_tl_kredi_karti.py
```

**`chappie/` proje disinda durur.** Boylece ayni paket birden cok test projesi tarafindan paylasilabilir; her projeye kopyalanmasi gerekmez. `tests/chappie_entegrasyon.py` bir ust dizini `sys.path`e ekleyerek paketi bulur.

## Kim ne yapar

- **`chappie/`** — robotu surer. Karti okutur, PIN'e basar. Bu projeyi, testleri, sayfalari **tanimaz**.
- **`pages/`** — ekranlari tanir: locatorlar ve o ekranda yapilabilecekler. Robottan **habersizdir**; yalnizca bekler ve gecer.
- **`tests/`** — senaryoyu surer. Hangi adimda robotun ne yapacagina **test karar verir**.

Arada sarmalayici, yama ya da gizli otomatik davranis yoktur. Komutu her zaman test verir:

```python
kart_okutma = odeme_al.kredi_karti_ile_ode()          # sayfa: ekrana gel
chappie.karti_okut()                                  # chappie: karti okut
kart_okutma.kart_okutulmasini_bekle(timeout=30)       # sayfa: ekran kapandi mi
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

Tezgahla ilgili her sey `chappie/chappie.json` dosyasinda. Oncelik:

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

## Testin akisi

1. Satis ekraninda `3500` yazilir, ilk kisma tiklanir (sepete kalem eklenir)
2. Devam -> Odeme al -> Kredi K.
3. "Lutfen karti okutun" ekrani beklenir; **chappie karti NFC'ye okutur**
4. Satis Tipi ve Kasiyer No ekranlari **cikarlarsa** gecilir
5. PIN ekrani **cikarsa** **chappie PIN'i girer**
6. Is yeri nushasi yazdirilir, Satis ekranina donulur
7. Kart rafa geri konur (`finally` icinde -- test dusse de calisir)

4. ve 5. adimlarin opsiyonel olmasi kasitlidir: bazi kartlarda akis bu ekranlari atlar, cikmamalari hata degildir.

## Yeni test eklemek

`tests/` altina bir dosya acin, `chappie` fixture'ini isteyin:

```python
def test_yeni_senaryo(driver, chappie):
    satis = SatisPage(driver)
    satis.tutar_gir("100")
    satis.ilk_kismi_sec()

    kart_okutma = satis.devam_tikla().kredi_karti_ile_ode()
    chappie.karti_tak()          # cipe tak -- NFC yerine
    kart_okutma.kart_okutulmasini_bekle(timeout=30)
```

Kullanilabilir komutlar `tests/chappie_entegrasyon.py` dosyasinin basinda listelenmistir.

## Sorun giderme

**Robot kimildamiyor** — `python tests/chappie_entegrasyon.py` calistirin. Adimlar sirayla raporlanir; ilk basarisiz adim gercek sebeptir.

**`Queue is empty, sending 0`** — hata **degildir**. Surucunun bosta kalma sinyalidir; robot bostayken saniyede bir yazar ve yazmasi durmamalidir. Anlamli olan, ilk komuttan **sonra** ne yazdigidir.

**Surucu gunlugu** — `chappie_surucu.log`. Surucu process'inin tum ciktisi oraya yazilir; pytest onu yakalamaz.

**Kart kiskacta kaldi** — bir sonraki kosumun ilk hareketi raftaki karta carpar. Test `finally` icinde `chappie.temizle()` cagirir; yine de takildiysa elle alin.
