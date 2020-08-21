from ..api import API

_api = API.get_instance()


def auth(path_to_config_json):
    """Authenticates to Superannotate platform using the config file.

    :param path_to_config_json: Location to config JSON
    :type path_to_config_json:
    """
    _api.set_auth(path_to_config_json)
