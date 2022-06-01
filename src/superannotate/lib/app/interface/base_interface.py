import functools
import sys
from abc import ABC
from abc import abstractmethod
from inspect import signature
from types import FunctionType
from typing import Iterable
from typing import Sized

from lib.app.helpers import extract_project_folder
from lib.core.reporter import Session
from mixpanel import Mixpanel
from version import __version__


class BaseInterfaceFacade(ABC):
    @property
    @abstractmethod
    def host(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def token(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def logger(self):
        raise NotImplementedError


class Tracker:
    TEAM_DATA = None
    INITIAL_EVENT = {"event_name": "SDK init", "properties": {}}
    INITIAL_LOGGED = False

    @staticmethod
    def get_mp_instance() -> Mixpanel:
        # if "api.annotate.online" in get_default_controller()._backend_url:
        #     return Mixpanel("ca95ed96f80e8ec3be791e2d3097cf51")
        return Mixpanel("e741d4863e7e05b1a45833d01865ef0d")

    @staticmethod
    def get_default_payload(team_name, user_id, project_name=None):
        return {
            "SDK": True,
            "Paid": True,
            "Team": team_name,
            "Team Owner": user_id,
            "Project Name": project_name,
            "Project Role": "Admin",
            "Version": __version__,
        }

    def __init__(self, function):
        self.function = function
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
            elif key == "project":
                (
                    properties["project_name"],
                    properties["folder_name"],
                ) = extract_project_folder(value)
            elif isinstance(value, (str, int, float, bool, str)):
                properties[key] = value
            elif isinstance(value, dict):
                properties[key] = value.keys()
            elif isinstance(value, Sized):
                properties[key] = len(value)
            elif isinstance(value, Iterable):
                properties[key] = "N/A"
            else:
                properties[key] = str(value)
        return function_name, properties

    def track(self, args, kwargs, success: bool, session):
        try:
            function_name = self.function.__name__ if self.function else ""
            arguments = self.extract_arguments(self.function, *args, **kwargs)
            event_name, properties = self.default_parser(function_name, arguments)

            user_id = self.team_data.creator_id
            team_name = self.team_data.name
            properties["Success"] = success

            default = self.get_default_payload(
                team_name=team_name,
                user_id=user_id,
                project_name=properties.pop("project_name", None),
            )
            if "pytest" not in sys.modules:
                self.get_mp_instance().track(
                    user_id, event_name, {**default, **properties, **session.data}
                )
        except Exception:
            raise

    def __get__(self, instance, owner):
        if instance is None:
            return self
        d = self
        mfactory = lambda self, *args, **kw: d(self, *args, **kw)
        mfactory.__name__ = self.function.__name__
        self.team_data = instance.controller.team_data.data
        return mfactory.__get__(instance, owner)

    def __call__(self, *args, **kwargs):
        success = True
        try:
            with Session(self.function.__name__) as session:
                result = self.function(*args, **kwargs)
        except Exception as e:
            success = False
            raise e
        else:
            return result
        finally:
            self.track(args=args, kwargs=kwargs, success=success, session=session)


class TrackableMeta(type):
    def __new__(mcs, name, bases, attrs):
        for attr_name, attr_value in attrs.iteritems():
            if isinstance(attr_value, FunctionType):
                attrs[attr_name] = mcs.decorate(attr_value)
        return super().__new__(mcs, name, bases, attrs)

    @staticmethod
    def decorate(func):
        return Tracker(func)
