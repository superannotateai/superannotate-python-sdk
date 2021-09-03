import functools
import sys

from mixpanel import Mixpanel
from superannotate.lib.infrastructure.controller import Controller
from superannotate.version import __version__

from .config import TOKEN
from .utils import parsers

mp = Mixpanel(TOKEN)

controller = Controller.get_instance()


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
    def __init__(self, function):
        self.function = function
        self._success = False
        functools.update_wrapper(self, function)

    def track(self, *args, **kwargs):
        try:
            data = getattr(parsers, self.function.__name__)(*args, **kwargs)
            event_name = data["event_name"]
            properties = data["properties"]
            properties["Success"] = self._success
            default = get_default(
                team_name=controller.team_name,
                user_id=controller.user_id,
                project_name=properties.get("project_name", None),
            )
            properties.pop("project_name", None)
            properties = {**default, **properties}

            if "pytest" not in sys.modules:
                mp.track(controller.user_id, event_name, properties)
        except Exception as _:
            pass

    def __call__(self, *args, **kwargs):
        try:
            ret = self.function(*args, **kwargs)
            self._success = True
            self.track(*args, **kwargs)
        except Exception as e:
            self._success = False
            self.track(*args, **kwargs)
            raise e
        return ret
