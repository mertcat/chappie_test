"""Test process'i ile robot sürücüsü arasındaki paylaşılan durum.

Kaynağı chappieautomation/shared_data.py; API'si AYNEN korundu (behave tarafı
``edit_shared_value`` / ``set_event`` / ``robot_lock_acquire`` gibi metotları
kullanıyor, o yüzden hiçbiri kaldırılmadı).

Robot ayrı bir process'te koştuğu için iki taraf da aynı nesneye doğrudan erişemez;
paylaşım ``multiprocessing.Manager`` proxy'leriyle yapılır:

  queue_of_commands  test -> robot komut kuyruğu
  io_elements        robot -> test IO sinyalleri (Job_OK, Gripper_Kart, M<n>_Kartvar)
  terminate_event    test -> robot "döngüden çık" işareti
"""
import multiprocessing
from time import sleep


class Paylasim:
    """Process'ler arası paylaşılan kuyruk, sinyaller ve olaylar."""

    def __init__(self):
        self._queue_of_commands = multiprocessing.Manager().Queue(20)
        self._shared_dict = multiprocessing.Manager().dict()
        self._io_elements = multiprocessing.Manager().dict()
        self.lock = multiprocessing.Lock()
        self.event = multiprocessing.Event()
        self.robot_event = multiprocessing.Event()
        self.robot_lock = multiprocessing.Lock()
        self.inverted_robot_event = multiprocessing.Event()
        self.terminate_event = multiprocessing.Event()

    @property
    def shared_dict(self):
        return self._shared_dict

    @property
    def io_elements(self):
        return self._io_elements

    @property
    def queue_of_commands(self):
        return self._queue_of_commands

    def sinyal(self, ad, varsayilan=None):
        """IO sinyalinin son bilinen değeri; sinyal hiç gelmediyse ``varsayilan``.

        DİKKAT: sözlük BOŞ olabilir -- WebSocket aboneliği kurulamadıysa sürücü
        bunu fark etmez (kendi Job_OK varsayılanı 1'dir) ve boşta dönmeye devam
        eder. Bu yüzden çağıran taraf "anahtar yok" ile "değer 0" arasındaki farkı
        önemsiyorsa varsayilan=None geçip ayırt etmeli.
        """
        deger = self._io_elements.get(ad)
        return varsayilan if deger is None else int(deger)

    def edit_shared_value(self, key, new_value):
        """Paylaşılan datayı aynı anda tek process editleyebilsin diye kilitleyerek yazar."""
        with self.lock:
            self._shared_dict[key] = new_value
        self.event.set()
        return self.shared_dict

    def get_shared_dict_key_value(self, key):
        return self._shared_dict[key]

    def set_event(self, event_name):
        if event_name == "robot_event":
            self.robot_event.set()
            self.robot_lock.acquire()
            self.inverted_robot_event.clear()

    def clear_events(self):
        """Olayları sıfırlar; paylaşılan datayı da varsayılana döndürür."""
        self.event.clear()
        self.robot_event.clear()
        self.robot_lock.release()
        self.inverted_robot_event.set()

    def wait_event_clear(self, event_name):
        if event_name == "robot_event":
            while True:
                if self.get_event("robot_event") is False:
                    break
                sleep(1)
            self.set_event("robot_event")
        else:
            self.event.wait(100)

    def get_event(self, event_name):
        if event_name == "robot_event":
            return self.robot_event.is_set()
        if event_name == "inverted_robot_event":
            return self.inverted_robot_event.is_set()
        return None

    def robot_lock_acquire(self):
        self.robot_lock.acquire()

    def robot_lock_release(self):
        self.robot_lock.release()
