import functools
import sys
from inspect import signature

from lib import get_default_controller
from mixpanel import Mixpanel
from superannotate.logger import get_default_logger
from version import __version__

from .utils import parsers

logger = get_default_logger()


def get_mp_instance() -> Mixpanel:
    if "api.annotate.online" in get_default_controller()._backend_url:
        return Mixpanel("ca95ed96f80e8ec3be791e2d3097cf51")
    return Mixpanel("e741d4863e7e05b1a45833d01865ef0d")


def get_default(team_name, user_id, project_name=None):
    return {
        "SDK": True,
        "Paid": True,
        "Team": team_name,
        "Team Owner": user_id,
        "Project Name": project_name,
        "Project Role": "Admin",
        "Version": __version__,
    }


class Trackable:
    TEAM_DATA = None
    INITIAL_EVENT = {"event_name": "SDK init", "properties": {}}
    INITIAL_LOGGED = False

    def __init__(self, function, initial=False):
        self.function = function
        self._success = False
        self._initial = initial
        if initial:
            self.track()
        functools.update_wrapper(self, function)

    @staticmethod
    def extract_arguments(function, *args, **kwargs) -> dict:
        bound_arguments = signature(function).bind(*args, **kwargs)
        bound_arguments.apply_defaults()
        return dict(bound_arguments.arguments)

    @property
    def team(self):
        return get_default_controller().get_team()

    @staticmethod
    def default_parser(function_name: str, kwargs: dict):
        properties = {}
        for key, value in kwargs:
            if isinstance(value, (str, int, float, bool, str)):
                properties[key] = value
            elif isinstance(value, (list, set, tuple)):
                properties[key] = len(value)
            elif isinstance(value, dict):
                properties[key] = value.keys()
            elif hasattr(value, "__len__"):
                properties[key] = len(value)
            else:
                properties[key] = str(value)
        return {
            "event_name": function_name,
            "properties": properties
        }

    def track(self, *args, **kwargs):
        try:
            function_name = self.function.__name__ if self.function else ""
            if self._initial:
                data = self.INITIAL_EVENT
                Trackable.INITIAL_LOGGED = True
                self._success = True
            else:
                data = {}
                arguments = self.extract_arguments(self.function, *args, **kwargs)
                if hasattr(parsers, function_name):
                    try:
                        data = getattr(parsers, function_name)(**arguments)
                    except Exception:
                        pass
                else:
                    data = self.default_parser(function_name, arguments)
            event_name = data.get("event_name", )
            properties = data.get("properties", {})
            team_data = self.team.data
            user_id = team_data.creator_id
            team_name = team_data.name
            properties["Success"] = self._success
            default = get_default(
                team_name=team_name,
                user_id=user_id,
                project_name=properties.get("project_name", None),
            )
            properties.pop("project_name", None)
            properties = {**default, **properties}

            if "pytest" not in sys.modules:
                get_mp_instance().track(user_id, event_name, properties)
        except Exception:
            pass

    def __call__(self, *args, **kwargs):
        try:
            controller = get_default_controller()
            if controller:
                self.__class__.TEAM_DATA = controller.get_team()
                result = self.function(*args, **kwargs)
                self._success = True
            else:
                raise Exception(
                    "SuperAnnotate config file not found."
                    " Please provide correct config file location to sa.init(<path>) or use "
                    "CLI's superannotate init to generate default location config file."
                )
        except Exception as e:
            self._success = False
            logger.debug(str(e), exc_info=True)
            raise e
        else:
            return result
        finally:
            try:
                self.track(*args, **kwargs)
            except Exception:
                pass


if __name__ == "lib.app.mixp.decorators" and not Trackable.INITIAL_LOGGED:
    Trackable(None, initial=True)
