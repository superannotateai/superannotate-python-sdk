parsers = {}


def get_team_metadata(*args, **kwargs):
    return {"event_name": "get_team_metadata", "properties": {}}


parsers['get_team_metadata'] = get_team_metadata
