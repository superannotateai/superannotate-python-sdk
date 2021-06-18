import logging

import lib.core as constances
from lib.infrastructure.controller import Controller
from src.lib.core.response import Response
from src.lib.infrastructure.repositories import ConfigRepository
from src.lib.infrastructure.services import SuperannotateBackendService


logger = logging.getLogger()


class BaseInterfaceFacade:
    @property
    def controller(self):
        return Controller(
            backend_client=SuperannotateBackendService(
                api_url=constances.BACKEND_URL,
                auth_token=ConfigRepository().get_one("token"),
                logger=logger,
            ),
            response=Response(),
        )
