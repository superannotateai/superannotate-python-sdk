import sys
from .parsers import parsers
from .app import mp, get_default
from superannotate.api import API

_api = API.get_instance()
callers_to_ignore = []


def trackable(func):
    callers_to_ignore.append(func.__name__)

    def wrapper(*args, **kwargs):
        if 1:
            caller_function_name = sys._getframe().f_back.f_code.co_name
            if caller_function_name not in callers_to_ignore:
                func_name_to_track = func.__name__
                data = parsers[func_name_to_track](*args, **kwargs)
                user_id = _api.user_id
                event_name = data['event_name']
                properties = data['properties']
                default = get_default(
                    _api.team_name,
                    _api.user_id,
                    project_name=properties.get('project_name', None)
                )
                properties = {**default, **properties}
                mp.track(user_id, event_name, properties)
        # except Exception as e:
        #     print("--- ---- --- MIX PANEL EXCEPTION")
        return func(*args, **kwargs)

    return wrapper
