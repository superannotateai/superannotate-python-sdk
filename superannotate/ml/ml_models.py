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

def _get_model_id_if_exists(model, prohect_type):

    model_name = None
    model_id = None

    if isinstance(model, dict):
        model_name = model["name"]
    elif isinstance(model, str):
        params = {
            "type" : project_type,
            "include_global": True,
            "team_id": _api.team_id
        }

        response = _api.send_request(
            req_type = "GET",
            path = f"/ml_models",
            params = params
        )

        if not response.ok:
            raise SABaseException(
                0, "Could not fetch information about available models, please try again"
            )

        data = response.json()
        data= {x['name'] : x['id'] for x in data}


    raise NotImplementedError

