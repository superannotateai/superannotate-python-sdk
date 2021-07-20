import functools
import sys
from .app import mp, get_default
from superannotate.api import API
from .utils import parsers
from threading import Lock
from functools import wraps
from .helper import CALLERS_TO_IGNORE

_api = API.get_instance()
always_trackable_func_names = ["upload_images_from_folder_to_project"]


class Trackable(object):
    registered = set(CALLERS_TO_IGNORE)

    def __init__(self, function):
        lock = Lock()
        self.function = function
        self._success = None
        self._caller_name = None
        self._func_name_to_track = None
        with lock:
            Trackable.registered.add(function.__name__)
        functools.update_wrapper(self, function)

    def should_track(self):
        if self._caller_name not in Trackable.registered or self._func_name_to_track in always_trackable_func_names:
            return True
        return False

    def track(self, *args, **kwargs):
        try:
            if self.should_track():
                data = getattr(parsers, self._func_name_to_track)(*args, **kwargs)
                user_id = _api.user_id
                event_name = data['event_name']
                properties = data['properties']
                properties['Success'] = self._success
                default = get_default(
                    _api.team_name,
                    _api.user_id,
                    project_name=properties.get('project_name', None)
                )
                properties.pop("project_name", None)
                properties = {**default, **properties}
                if "pytest" not in sys.modules:
                    mp.track(user_id, event_name, properties)
        except Exception as e:
            pass


    def __call__(self, *args, **kwargs):
        try:
            self._caller_name = sys._getframe(1).f_code.co_name
            self._func_name_to_track = self.function.__name__
            ret = self.function(*args, **kwargs)
            self._success = True
            self.track(*args, **kwargs)
        except Exception as e:
            self._success = False
            self.track(*args, **kwargs)
            raise e
        return ret
