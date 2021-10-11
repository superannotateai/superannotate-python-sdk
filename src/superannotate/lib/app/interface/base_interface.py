import logging

from lib.infrastructure.controller import Controller
from lib.infrastructure.repositories import ConfigRepository


logger = logging.getLogger()


class BaseInterfaceFacade:
    def __init__(self):
        self._config_path = None

    @property
    def controller(self):
        if not ConfigRepository().get_one("token"):
            raise Exception("Config does not exists!")
        if self._config_path:
            return Controller(logger, self._config_path)
        return Controller(logger)
