parsers = {}


def get_project_root_folder_id_parser(*args, **kwargs):
    return {"event_name": "some_name", "properties": {"prop1": "value1"}}


parsers['get_project_root_folder_id'] = get_project_root_folder_id_parser
