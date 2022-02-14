from lib import get_default_controller
from lib.infrastructure.repositories import ConfigRepository


class BaseInterfaceFacade:
    def __init__(self):
        self._config_path = None
        self._controller = get_default_controller()

    @property
    def controller(self):
        if not ConfigRepository().get_one("token"):
            raise Exception("Config does not exists!")
        return self._controller
