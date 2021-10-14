from lib.infrastructure.controller import Controller
from lib.infrastructure.repositories import ConfigRepository


class BaseInterfaceFacade:
    def __init__(self):
        self._config_path = None

    @property
    def controller(self):
        if not ConfigRepository().get_one("token"):
            raise Exception("Config does not exists!")
        controller = Controller.get_instance()
        if self._config_path:
            controller.init(self._config_path)
        return controller
