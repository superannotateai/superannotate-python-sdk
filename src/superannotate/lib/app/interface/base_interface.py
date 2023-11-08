import functools
import json
import os
import platform
import sys
import typing
from inspect import signature
from pathlib import Path
from types import FunctionType
from typing import Iterable
from typing import Sized

import lib.core as constants
from lib.app.interface.types import validate_arguments
from lib.core import CONFIG
from lib.core import setup_logging
from lib.core.entities.base import ConfigEntity
from lib.core.entities.base import TokenStr
from lib.core.exceptions import AppException
from lib.core.pydantic_v1 import ErrorWrapper
from lib.core.pydantic_v1 import ValidationError
from lib.infrastructure.controller import Controller
from lib.infrastructure.utils import extract_project_folder
from lib.infrastructure.validators import wrap_error
from mixpanel import Mixpanel
from superannotate import __version__


class BaseInterfaceFacade:
    REGISTRY = []

    @validate_arguments
    def __init__(self, token: TokenStr = None, config_path: str = None):
        try:
            if token:
                config = ConfigEntity(SA_TOKEN=token)
            elif config_path:
                config_path = Path(config_path).expanduser()
                if not Path(config_path).is_file() or not os.access(
                    config_path, os.R_OK
                ):
                    raise AppException(
                        f"SuperAnnotate config file {str(config_path)} not found."
                    )
                if config_path.suffix == ".json":
                    config = self._retrieve_configs_from_json(config_path)
                else:
                    config = self._retrieve_configs_from_ini(config_path)

            else:
                config = self._retrieve_configs_from_env()
                if not config:
                    if Path(constants.CONFIG_INI_FILE_LOCATION).exists():
                        config = self._retrieve_configs_from_ini(
                            constants.CONFIG_INI_FILE_LOCATION
                        )
                    elif Path(constants.CONFIG_JSON_FILE_LOCATION).exists():
                        config = self._retrieve_configs_from_json(
                            constants.CONFIG_JSON_FILE_LOCATION
                        )
                    else:
                        raise AppException(
                            f"SuperAnnotate config file {constants.CONFIG_INI_FILE_LOCATION} not found."
                        )
        except ValidationError as e:
            raise AppException(wrap_error(e))
        except KeyError:
            raise
        if not config:
            raise AppException("Credentials not provided.")
        setup_logging(config.LOGGING_LEVEL, config.LOGGING_PATH)
        self.controller = Controller(config)
        BaseInterfaceFacade.REGISTRY.append(self)

    @staticmethod
    def _retrieve_configs_from_json(path: Path) -> typing.Union[ConfigEntity]:
        with open(path) as json_file:
            json_data = json.load(json_file)
        token = json_data["token"]
        try:
            config = ConfigEntity(SA_TOKEN=token)
        except ValidationError:
            raise ValidationError(
                [ErrorWrapper(ValueError("Invalid token."), loc="token")],
                model=ConfigEntity,
            )
        host = json_data.get("main_endpoint")
        verify_ssl = json_data.get("ssl_verify")
        if host:
            config.API_URL = host
        if verify_ssl:
            config.VERIFY_SSL = verify_ssl
        return config

    @staticmethod
    def _retrieve_configs_from_ini(path: Path) -> typing.Union[ConfigEntity]:
        import configparser

        config_parser = configparser.ConfigParser()
        config_parser.optionxform = str
        config_parser.read(path)
        config_data = {}
        for key in config_parser["DEFAULT"]:
            config_data[key.upper()] = config_parser["DEFAULT"][key]
        return ConfigEntity(**config_data)

    @staticmethod
    def _retrieve_configs_from_env() -> typing.Union[ConfigEntity, None]:
        token = os.environ.get("SA_TOKEN")
        if not token:
            return None
        config = ConfigEntity(**dict(os.environ))
        host = os.environ.get("SA_URL")
        verify_ssl = not os.environ.get("SA_SSL", "True").lower() in ("false", "f", "0")
        if host:
            config.API_URL = host
        if verify_ssl:
            config.VERIFY_SSL = verify_ssl
        return config


class Tracker:
    def get_mp_instance(self) -> Mixpanel:
        client = self.get_client()
        if client.controller._config.API_URL == constants.BACKEND_URL:  # noqa
            mp_token = "ca95ed96f80e8ec3be791e2d3097cf51"
        else:
            mp_token = "e741d4863e7e05b1a45833d01865ef0d"
        return Mixpanel(mp_token)

    @staticmethod
    def get_default_payload(team_name, user_email):
        return {
            "SDK": True,
            "Team": team_name,
            "User Email": user_email,
            "Version": __version__,
            "Python version": platform.python_version(),
            "Python interpreter type": platform.python_implementation(),
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
            elif key == "token":
                properties["sa_token"] = str(bool(value))
            elif key == "config_path":
                properties[key] = str(bool(value))
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
            user_email = client.controller.current_user.email
            team_name = client.controller.team_data.name

            properties["Success"] = success
            default = self.get_default_payload(
                team_name=team_name, user_email=user_email
            )
            self._track(
                user_email,
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
        attrs["__init__"] = Tracker(validate_arguments(attrs["__init__"]))
        tmp = super().__new__(mcs, name, bases, attrs)
        return tmp
