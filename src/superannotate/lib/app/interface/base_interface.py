import functools
import os
import sys
from inspect import signature
from pathlib import Path
from types import FunctionType
from typing import Iterable
from typing import Sized
from typing import Tuple

import lib.core as constants
from lib.app.helpers import extract_project_folder
from lib.app.interface.types import validate_arguments
from lib.core import CONFIG
from lib.core.exceptions import AppException
from lib.infrastructure.controller import Controller
from lib.infrastructure.repositories import ConfigRepository
from mixpanel import Mixpanel
from version import __version__


class BaseInterfaceFacade:
    REGISTRY = []

    def __init__(self, token: str = None, config_path: str = None):
        version = os.environ.get("SA_VERSION", "v1")
        _token, _config_path = None, None
        _host = os.environ.get("SA_URL", constants.BACKEND_URL)
        _ssl_verify = bool(os.environ.get("SA_SSL", True))
        if token:
            _token = Controller.validate_token(token=token)
        elif config_path:
            _token, _host, _ssl_verify = self._retrieve_configs(config_path)
        else:
            _token = os.environ.get("SA_TOKEN")
            if not _token:
                _toke, _host, _ssl_verify = self._retrieve_configs(
                    constants.CONFIG_PATH
                )
        self._token, self._host = _host, _token
        self.controller = Controller(_token, _host, _ssl_verify, version)

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        cls.REGISTRY.append(obj)
        return obj

    @staticmethod
    def _retrieve_configs(path) -> Tuple[str, str, str]:
        config_path = os.path.expanduser(str(path))
        if not Path(config_path).is_file() or not os.access(config_path, os.R_OK):
            raise AppException(
                f"SuperAnnotate config file {str(config_path)} not found."
                f" Please provide correct config file location to sa.init(<path>) or use "
                f"CLI's superannotate init to generate default location config file."
            )
        config_repo = ConfigRepository(config_path)
        return (
            Controller.validate_token(config_repo.get_one("token").value),
            config_repo.get_one("main_endpoint").value,
            config_repo.get_one("ssl_verify").value,
        )

    @property
    def host(self):
        return self._host

    @property
    def token(self):
        return self._token


class Tracker:
    def get_mp_instance(self) -> Mixpanel:
        if self.client:
            if self.client.host == constants.BACKEND_URL:
                return Mixpanel("ca95ed96f80e8ec3be791e2d3097cf51")
            else:
                return Mixpanel("e741d4863e7e05b1a45833d01865ef0d")

    @staticmethod
    def get_default_payload(team_name, user_id):
        return {
            "SDK": True,
            "Team": team_name,
            "Team Owner": user_id,
            "Version": __version__,
        }

    def __init__(self, function):
        self.function = function
        self._client = None
        functools.update_wrapper(self, function)

    @property
    def client(self):
        if not self._client:
            if BaseInterfaceFacade.REGISTRY:
                self._client = BaseInterfaceFacade.REGISTRY[-1]
            else:
                from lib.app.interface.sdk_interface import SAClient

                self._client = SAClient()
        return self._client

    @staticmethod
    def extract_arguments(function, *args, **kwargs) -> dict:
        bound_arguments = signature(function).bind(*args, **kwargs)
        bound_arguments.apply_defaults()
        return dict(bound_arguments.arguments)

    @staticmethod
    def default_parser(function_name: str, kwargs: dict) -> tuple:
        properties = {}
        for key, value in kwargs.items():
            if key == "self":
                continue
            elif value is None:
                properties[key] = value
            elif key == "project":
                properties["project_name"], folder_name = extract_project_folder(value)
                if folder_name:
                    properties["folder_name"] = folder_name
            elif isinstance(value, (str, int, float, bool)):
                properties[key] = value
            elif isinstance(value, dict):
                properties[key] = list(value.keys())
            elif isinstance(value, Sized):
                properties[key] = len(value)
            elif isinstance(value, Iterable):
                properties[key] = "N/A"
            else:
                properties[key] = str(value)
        return function_name, properties

    def _track(self, user_id: str, event_name: str, data: dict):
        if "pytest" not in sys.modules:
            self.get_mp_instance().track(user_id, event_name, data)

    def _track_method(self, args, kwargs, success: bool):
        function_name = self.function.__name__ if self.function else ""
        arguments = self.extract_arguments(self.function, *args, **kwargs)
        event_name, properties = self.default_parser(function_name, arguments)

        user_id = self.client.controller.team_data.creator_id
        team_name = self.client.controller.team_data.name

        properties["Success"] = success
        default = self.get_default_payload(team_name=team_name, user_id=user_id)
        self._track(
            user_id,
            event_name,
            {**default, **properties, **CONFIG.get_current_session().data},
        )

    def __get__(self, obj, owner=None):
        if obj is not None:
            self._client = obj
            tmp = functools.partial(self.__call__, obj)
            functools.update_wrapper(tmp, self.function)
            return tmp
        return self

    def __call__(self, *args, **kwargs):
        success = True
        try:
            result = self.function(*args, **kwargs)
        except Exception as e:
            success = False
            raise e
        else:
            return result
        finally:
            self._track_method(args=args, kwargs=kwargs, success=success)


class TrackableMeta(type):
    def __new__(mcs, name, bases, attrs):
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, FunctionType):
                attrs[attr_name] = Tracker(validate_arguments(attr_value))
        tmp = super().__new__(mcs, name, bases, attrs)
        return tmp
