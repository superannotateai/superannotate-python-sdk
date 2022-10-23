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
from lib.app.interface.types import validate_arguments
from lib.core import CONFIG
from lib.core.exceptions import AppException
from lib.infrastructure.controller import Controller
from lib.infrastructure.repositories import ConfigRepository
from lib.infrastructure.utils import extract_project_folder
from mixpanel import Mixpanel
from superannotate import __version__


class BaseInterfaceFacade:
    REGISTRY = []

    def __init__(self, token: str = None, config_path: str = None):
        version = os.environ.get("SA_VERSION", "v1")
        _token, _config_path = None, None
        _host = os.environ.get("SA_URL", constants.BACKEND_URL)
        _ssl_verify = not os.environ.get("SA_SSL", "True").lower() in (
            "false",
            "f",
            "0",
        )
        if token:
            _token = Controller.validate_token(token=token)
        elif config_path:
            _token, _host, _ssl_verify = self._retrieve_configs(config_path)
        else:
            _token = os.environ.get("SA_TOKEN")
            if not _token:
                _token, _host, _ssl_verify = self._retrieve_configs(
                    constants.CONFIG_PATH
                )
        _host = _host if _host else constants.BACKEND_URL
        _ssl_verify = True if _ssl_verify is None else _ssl_verify

        self._token, self._host = _token, _host
        self.controller = Controller(_token, _host, _ssl_verify, version)
        BaseInterfaceFacade.REGISTRY.append(self)

    @staticmethod
    def _retrieve_configs(path) -> Tuple[str, str, str]:
        config_path = os.path.expanduser(str(path))
        if not Path(config_path).is_file() or not os.access(config_path, os.R_OK):
            raise AppException(
                f"SuperAnnotate config file {str(config_path)} not found."
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
        client = self.get_client()
        mp_token = "ca95ed96f80e8ec3be791e2d3097cf51"
        if client:
            if client.host != constants.BACKEND_URL:
                mp_token = "e741d4863e7e05b1a45833d01865ef0d"
        return Mixpanel(mp_token)

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

    def get_client(self):
        if not self._client:
            if BaseInterfaceFacade.REGISTRY:
                return BaseInterfaceFacade.REGISTRY[-1]
            else:
                from lib.app.interface.sdk_interface import SAClient

                try:
                    return SAClient()
                except Exception:
                    pass
        elif hasattr(self._client, "controller"):
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
        try:
            client = self.get_client()
            if not client:
                return
            function_name = self.function.__name__ if self.function else ""
            arguments = self.extract_arguments(self.function, *args, **kwargs)
            event_name, properties = self.default_parser(function_name, arguments)
            user_id = client.controller.team_data.creator_id
            team_name = client.controller.team_data.name

            properties["Success"] = success
            default = self.get_default_payload(team_name=team_name, user_id=user_id)
            self._track(
                user_id,
                event_name,
                {**default, **properties, **CONFIG.get_current_session().data},
            )
        except BaseException:
            pass

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
            if isinstance(
                attr_value, FunctionType
            ) and not attr_value.__name__.startswith("_"):
                attrs[attr_name] = Tracker(validate_arguments(attr_value))
        tmp = super().__new__(mcs, name, bases, attrs)
        return tmp
