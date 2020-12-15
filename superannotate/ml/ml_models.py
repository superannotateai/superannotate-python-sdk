import logging
from ..api import API
from ..exceptions import SABaseException
logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


def search_models(
    name = None,
    type_ = None,
    project_id = None,
    task = None,
    include_global = True,
):
    params = {
        "name":name,
        "team_id":_api.team_id,
        "project_id": project_id,
        "task": task,
        "type": type_,
        "includ_global":include_global
    }

    response = _api.send_request(
        req_type = "GET",
        path = f"/ml_models",
        params = params
    )

    if not response.ok:
        raise SABaseException(
            0, "could not search models"
        )
    result = response.json()
    if not result['data']:
        raise SABaseException(
            0, "Model with such a name does not exist"
        )
    return result['data']

