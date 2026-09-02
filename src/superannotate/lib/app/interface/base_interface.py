import functools
import json
import os
import platform
import sys
from collections.abc import Iterable
from collections.abc import Sized
from functools import lru_cache
from inspect import signature
from pathlib import Path
from types import FunctionType

import lib.core as constants
from lib.app.interface.types import validate_arguments
from lib.core import CONFIG
from lib.core import setup_logging
from lib.core.auth_errors import CREDENTIALS_NOT_FOUND_ERROR
from lib.core.auth_errors import INVALID_CREDENTIALS_ERROR
from lib.core.auth_errors import INVALID_TEAM_ID_ERROR
from lib.core.auth_errors import INVALID_TOKEN_ERROR
from lib.core.entities.base import ConfigEntity
from lib.core.entities.base import TokenStr
from lib.core.exceptions import AppException
from lib.infrastructure.controller import Controller
from lib.infrastructure.utils import extract_project_folder_inputs
from lib.infrastructure.validators import wrap_error
from mixpanel import Mixpanel
from pydantic import ValidationError


class BaseInterfaceFacade:
    @validate_arguments
    def __init__(
        self,
        token: TokenStr | None = None,
        config_path: str | None = None,
        team_id: int | None = None,
        *,
        require_team: bool = True,
        require_organization: bool = False,
    ):
        config = self._resolve_config(token, config_path)
        if require_organization:
            # Organization-scoped: never team-bound, regardless of what SA_TEAM_ID/team_id
            # the config source happens to carry.
            config.TEAM_ID = None
        elif team_id is not None:
            # An explicit team_id wins over whatever the config source provided.
            config.TEAM_ID = team_id
        setup_logging(config.LOGGING_LEVEL, config.LOGGING_PATH)
        self.controller = Controller(
            config, require_team=require_team, require_organization=require_organization
        )

    @classmethod
    def _resolve_config(
        cls, token: str | None, config_path: str | None
    ) -> ConfigEntity:
        """Resolve credentials: explicit token, then config path, then env, then ini/json.

        Shared by every facade's ``__init__`` (``SAClient``, ``SAORGClient``).
        """
        try:
            if token:
                config = ConfigEntity(SA_TOKEN=token)
            elif config_path:
                config = cls._resolve_config_from_path(config_path)
            else:
                config = cls._resolve_config_from_env_or_files()
        except ValidationError as e:
            raise AppException(wrap_error(e))
        if not config:
            raise AppException(INVALID_CREDENTIALS_ERROR)
        return config

    @classmethod
    def _resolve_config_from_path(cls, config_path: str) -> ConfigEntity:
        """A config file the caller named explicitly (``.ini`` or ``.json``)."""
        path = Path(config_path).expanduser()
        if not path.is_file() or not os.access(path, os.R_OK):
            raise AppException(f"SuperAnnotate config file {path} not found.")
        if path.suffix == ".json":
            return cls._retrieve_configs_from_json(path)
        return cls._retrieve_configs_from_ini(path)

    @classmethod
    def _resolve_config_from_env_or_files(cls) -> ConfigEntity:
        """No token or config path given: ``SA_TOKEN``, then the default config files."""
        config = cls._retrieve_configs_from_env()
        if config:
            return config
        if Path(constants.CONFIG_INI_FILE_LOCATION).exists():
            return cls._retrieve_configs_from_ini(constants.CONFIG_INI_FILE_LOCATION)
        if Path(constants.CONFIG_JSON_FILE_LOCATION).exists():
            return cls._retrieve_configs_from_json(constants.CONFIG_JSON_FILE_LOCATION)
        raise AppException(CREDENTIALS_NOT_FOUND_ERROR)

    @staticmethod
    def _retrieve_configs_from_json(path: Path | str) -> ConfigEntity:
        with open(path) as json_file:
            json_data = json.load(json_file)
        token = json_data["token"]
        try:
            config = ConfigEntity(SA_TOKEN=token)
        except ValidationError:
            raise AppException(INVALID_TOKEN_ERROR)
        host = json_data.get("main_endpoint")
        verify_ssl = json_data.get("ssl_verify")
        team_id = json_data.get("team_id")
        if team_id is not None:
            config.TEAM_ID = int(team_id)
        if host:
            config.API_URL = host
        if verify_ssl:
            config.VERIFY_SSL = verify_ssl
        return config

    @staticmethod
    def _retrieve_configs_from_ini(path: Path | str) -> ConfigEntity:
        import configparser

        config_parser = configparser.ConfigParser()
        config_parser.optionxform = str
        config_parser.read(path)
        config_data = {}
        for key in config_parser["DEFAULT"]:
            config_data[key.upper()] = config_parser["DEFAULT"][key]
        return ConfigEntity(**config_data)

    @staticmethod
    def _retrieve_configs_from_env() -> ConfigEntity | None:
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
    def get_mp_instance(self, client, explicit_credentials: bool = False) -> Mixpanel:
        # client may have no .controller yet (e.g. __init__ failed before setting one).
        controller = getattr(client, "controller", None)
        if controller is not None:
            api_url = controller._config.API_URL  # noqa
        elif explicit_credentials:
            api_url = constants.BACKEND_URL
        else:
            api_url = os.environ.get("SA_URL", constants.BACKEND_URL)
        if api_url == constants.BACKEND_URL:
            mp_token = "ca95ed96f80e8ec3be791e2d3097cf51"
        else:
            mp_token = "e741d4863e7e05b1a45833d01865ef0d"
        return Mixpanel(mp_token)

    @staticmethod
    @lru_cache
    def get_default_payload(team_name, user_email, auth_type):
        return {
            "SDK": True,
            "Team": team_name,
            "User Email": user_email,
            # How the client authenticated (see TokenContext.auth_type_label).
            "Auth Type": auth_type,
            "Version": os.environ["sa_version"],
            "Python version": platform.python_version(),
            "Python interpreter type": platform.python_implementation(),
            "Env": os.environ.get("SA_ENV", "N/A"),
        }

    def __init__(self, function):
        self.function = function
        self.skip_flag = os.environ.get("SA_SKIP_METRICS", "False").lower() in (
            "true",
            "1",
            "t",
        )
        functools.update_wrapper(self, function)

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
            if key == "token":
                properties["sa_token"] = str(bool(value))
            elif key == "config_path":
                properties[key] = str(bool(value))
            elif value is None:
                properties[key] = value
            elif key == "project":
                properties.update(extract_project_folder_inputs(value))
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

    def _track(
        self,
        user_id: str,
        event_name: str,
        data: dict,
        *,
        client,
        explicit_credentials: bool = False,
    ):
        if "pytest" in sys.modules or self.skip_flag:
            return
        self.get_mp_instance(client, explicit_credentials).track(
            user_id, event_name, data
        )

    @classmethod
    def _failure_reason(
        cls, function_name: str, success: bool, error: BaseException | None
    ):
        """The original error message, for the "Auth Failure" event property.

        Scoped to __init__ auth/credential failures only.
        """
        if success or function_name != "__init__" or error is None:
            return None
        message = str(error)
        if any(
            marker in message
            for marker in (
                INVALID_CREDENTIALS_ERROR,
                INVALID_TEAM_ID_ERROR,
                INVALID_TOKEN_ERROR,
                CREDENTIALS_NOT_FOUND_ERROR,
            )
        ):
            return message
        return None

    def _track_method(
        self,
        instance,
        args,
        kwargs,
        success: bool,
        error: BaseException | None = None,
    ):
        try:
            function_name = self.function.__name__ if self.function else ""
            arguments = self.extract_arguments(self.function, *args, **kwargs)
            event_name, properties = self.default_parser(function_name, arguments)

            # instance is args[0] - the actual object the call was made on, captured
            # locally per call (see __call__), not shared/mutable state. It has no
            # .controller yet when __init__ fails before setting one.
            controller = getattr(instance, "controller", None)
            user_email = team_name = auth_type = None
            if controller is not None:
                user_email = controller.current_user.email
                token_context = controller.token_context
                auth_type = token_context.auth_type_label
                if token_context.team_id is not None:
                    team_name = controller.team.name
            elif instance is None:
                return

            properties["Success"] = success
            properties["Class"] = (
                instance.__class__.__name__ if instance is not None else None
            )
            properties["Auth Failure"] = self._failure_reason(
                function_name, success, error
            )
            default = self.get_default_payload(
                team_name=team_name, user_email=user_email, auth_type=auth_type
            )
            self._track(
                user_email or "",
                event_name,
                {**default, **properties, **CONFIG.get_current_session().data},
                client=instance,
                explicit_credentials=bool(
                    arguments.get("token") or arguments.get("config_path")
                ),
            )
        except BaseException:
            pass

    def __get__(self, obj, owner=None):
        if obj is not None:
            tmp = functools.partial(self.__call__, obj)
            functools.update_wrapper(tmp, self.function)
            return tmp
        return self

    def __call__(self, *args, **kwargs):
        success = True
        error = None
        # The instance the call is bound to (set by __get__ via functools.partial) -
        # captured locally here, per call, rather than read back from shared state.
        instance = args[0] if args else None
        try:
            result = self.function(*args, **kwargs)
        except Exception as e:
            success = False
            error = e
            raise e
        else:
            return result
        finally:
            self._track_method(
                instance, args=args, kwargs=kwargs, success=success, error=error
            )


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
