import sys
from .app import mp, get_default
from superannotate.api import API
from .utils import parsers
from threading import Lock
from functools import wraps

_api = API.get_instance()
always_trackable_func_names = ["upload_images_from_folder_to_project"]


class Trackable(object):
    registered = set('<module>')

    def __init__(self, function):
        lock = Lock()
        self.function = function
        with lock:
            Trackable.registered.add(function.__name__)

    def __call__(self, *args, **kwargs):
        try:
            func_name_to_track = self.function.__name__
            caller_name = sys._getframe(1).f_code.co_name
            if caller_name not in Trackable.registered or func_name_to_track in always_trackable_func_names:
                data = getattr(parsers, func_name_to_track)(*args, **kwargs)
                user_id = _api.user_id
                event_name = data['event_name']
                properties = data['properties']
                default = get_default(
                    _api.team_name,
                    _api.user_id,
                    project_name=properties.get('project_name', None)
                )
                properties.pop("project_name", None)
                properties = {**default, **properties}
                if "pytest" not in sys.modules:
                    mp.track(user_id, event_name, properties)
        except:
            pass
        return self.function(*args, **kwargs)
