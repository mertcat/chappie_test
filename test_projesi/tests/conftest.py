"""Ortak fixture'lar.

``chappie`` fixture'i tests/chappie_entegrasyon.py'den geliyor -- chappie ile
ilgili tek dosya odur.
"""
import pytest

from pages.driver_setup import surucu_olustur
# Chappie'nin projeye baglandigi TEK dosya. Bu satir olmadan `chappie` fixture'i
# testlerden gorunmez.
#
# pytest.ini icinde `-p tests.chappie_entegrasyon` ile eklenti olarak YUKLEMEYIN:
# -p eklentileri conftest toplanmasindan ONCE yuklenir, o anda proje koku
# sys.path'te olmadigindan `pytest` konsol betigiyle "No module named 'tests'"
# hatasi verir.
from tests.chappie_entegrasyon import chappie  # noqa: F401


@pytest.fixture(scope="session")
def driver():
    """Kosum boyunca TEK Appium oturumu."""
    surucu = surucu_olustur()
    yield surucu
    try:
        surucu.quit()
    except Exception:
        pass
