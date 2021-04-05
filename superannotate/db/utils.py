from ..api import API
from ..exceptions import SABaseException, SAImageSizeTooLarge
_api = API.get_instance()


def _get_upload_auth_token(params,project_id):
    response = _api.send_request(
        req_type='GET',
        path=f'/project/{project_id}/sdkImageUploadToken',
        params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get upload token " + response.text
        )
    
    res = response.json()
    return res

