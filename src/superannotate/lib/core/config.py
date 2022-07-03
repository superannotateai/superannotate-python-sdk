import threading
from typing import Dict

from dataclasses import dataclass
from dataclasses import field


class Session:
    def __init__(self):
        self.pk = threading.get_ident()
        self._data_dict = {}

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if type is not None:
            return False

    def __del__(self):
        Config().delete_current_session()

    @property
    def data(self):
        return self._data_dict

    @staticmethod
    def get_current_session():
        return Config().get_current_session()

    def __setitem__(self, key, item):
        self._data_dict[key] = item

    def __getitem__(self, key):
        return self._data_dict[key]

    def __repr__(self):
        return repr(self._data_dict)

    def clear(self):
        return self._data_dict.clear()


class Singleton(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass()
class Config(metaclass=Singleton):
    SESSIONS: Dict[int, Session] = field(default_factory=dict)

    def get_current_session(self):
        session = self.SESSIONS.get(threading.get_ident())
        if not session:
            session = Session()
            self.SESSIONS.update({session.pk: session})
        return session

    def delete_current_session(self):
        ident = threading.get_ident()
        if ident in self.SESSIONS:
            del self.SESSIONS[ident]
