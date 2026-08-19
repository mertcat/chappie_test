"""chappie -- ABB robot koluyla POS cihazına kart okutan test yardımcısı.

Her checklist projesine olduğu gibi kopyalanabilecek, kendi kendine yeten bir paket.
Robotu süren döngü de içinde olduğu için başka bir projeye bağımlı değildir.

    from chappie import Chappie, ChappieHazirDegil, erisilebilir_mi

    if not erisilebilir_mi():
        pytest.skip("robot ağda değil")

    with Chappie.baslat() as kol:
        kol.karti_okut()        # raftan al + temassız okut
        kol.pin_gir()           # PIN'i pinpad'den gir
        kol.karti_yerine_koy()

Tezgaha özel ayarlar (robot IP, makine/raf/kart, PIN'ler) ``chappie.ayarlar``da ve
hepsi ortam değişkeniyle ezilebilir -- paketi kopyaladığın projede kod değiştirmeden
tezgah değiştirebilirsin:

    ROBOT_MAKINE=1 ROBOT_KART=2 pytest ...

BAĞIMLILIKLAR: requests, xmltodict, ws4py

DİKKAT -- KOPYALAR AYRIŞIR: bu paket kopyala-yapıştır ile dağıtıldığı için bir
düzeltme diğer kopyalara KENDİLİĞİNDEN gitmez. Hangi kopyanın hangi sürümde olduğu
görülebilsin diye ``ayarlar.SURUM`` tutuluyor; bir kopyayı düzelttiğinde sürümü
artır ve diğerlerine yay.
"""
from chappie.ayarlar import SURUM
from chappie.guvenlik import KavramaDurumu, KavramaHatasi
from chappie.chappie import ChappieHazirDegil, Chappie
from chappie.paylasim import Paylasim
from chappie.surucu import erisilebilir_mi

__all__ = [
    "Chappie",
    "ChappieHazirDegil",
    "erisilebilir_mi",
    "KavramaHatasi",
    "KavramaDurumu",
    "Paylasim",
    "SURUM",
]
__version__ = SURUM
