import functools
import sys

from lib import get_default_controller
from mixpanel import Mixpanel
from superannotate.logger import get_default_logger
from version import __version__

from .utils import parsers


# TODO:
try:
    if "api.annotate.online" in get_default_controller()._backend_client.api_url:
        TOKEN = "ca95ed96f80e8ec3be791e2d3097cf51"
    else:
        TOKEN = "e741d4863e7e05b1a45833d01865ef0d"
except AttributeError as e:
    TOKEN = "e741d4863e7e05b1a45833d01865ef0d"
mp = Mixpanel(TOKEN)

logger = get_default_logger()


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

    @property
    def team(self):
        return get_default_controller().get_team()

    def track(self, *args, **kwargs):
        try:
            if self._initial:
                data = self.INITIAL_EVENT
                Trackable.INITIAL_LOGGED = True
                self._success = True
            else:
                data = getattr(parsers, self.function.__name__)(*args, **kwargs)
            event_name = data["event_name"]
            properties = data["properties"]
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
                mp.track(user_id, event_name, properties)
        except Exception as _:
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
                    f" Please provide correct config file location to sa.init(<path>) or use "
                    f"CLI's superannotate init to generate default location config file."
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
