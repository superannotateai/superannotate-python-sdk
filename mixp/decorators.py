import sys
from .parsers import parsers
from .app import mp
from superannotate.api import API

_api = API.get_instance()

func_names_to_ignore = []


def trackable(func):
    def wrapper(*args, **kwargs):
        try:
            caller_function_name = sys._getframe().f_back.f_code.co_name
            if caller_function_name not in func_names_to_ignore:
                func_name_to_track = func.__name__
                data = parsers[func_name_to_track](*args, **kwargs)
                user_id = _api.user_id
                event_name = data['event_name']
                properties = data['properties']
                properties['SDK'] = True
                properties['Paid'] = True
                properties['Team'] = _api.team_name
                properties['Team Owner'] = _api.user_id
                properties['Project Name'] = properties.get(
                    'project_name', None
                )
                properties['Project Role'] = "Admin"
                mp.track(user_id, event_name, properties)
        except Exception as e:
            print("--- ---- --- MIX PANEL EXCEPTION")
        return func(*args, **kwargs)

    return wrapper
