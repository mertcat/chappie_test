"""Testi calistirir.

    python main.py

Onkosullar:
  * Appium sunucusu acik olmali          appium
  * Cihaz adb'de gorunmeli               adb devices
  * Robot bu makinenin agindan erisilir olmali
    (kontrol: python tests/chappie_entegrasyon.py)
"""
import subprocess
import sys


def main():
    return subprocess.call([sys.executable, "-m", "pytest", "tests/", "-v"])


if __name__ == "__main__":
    sys.exit(main())
