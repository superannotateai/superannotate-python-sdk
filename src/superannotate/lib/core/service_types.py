from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from lib.core import entities
from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field
from pydantic import parse_obj_as


class Limit(BaseModel):
    max_image_count: Optional[int]
    remaining_image_count: int


class UserLimits(BaseModel):
    user_limit: Optional[Limit]
    project_limit: Limit
    folder_limit: Limit


class UploadAnnotationAuthData(BaseModel):
    access_key: str
    secret_key: str
    session_token: str
    region: str
    bucket: str
    images: Dict[int, dict]

    class Config:
        extra = Extra.allow
        fields = {
            "access_key": "accessKeyId",
            "secret_key": "secretAccessKey",
            "session_token": "sessionToken",
            "region": "region",
        }

    def __init__(self, **data):
        credentials = data["creds"]
        data.update(credentials)
        del data["creds"]
        super().__init__(**data)


class DownloadMLModelAuthData(BaseModel):
    access_key: str
    secret_key: str
    session_token: str
    region: str
    bucket: str
    paths: List[str]

    class Config:
        extra = Extra.allow
        fields = {
            "access_key": "accessKeyId",
            "secret_key": "secretAccessKey",
            "session_token": "sessionToken",
            "region": "region",
        }

    def __init__(self, **data):
        credentials = data["tokens"]
        data.update(credentials)
        del data["tokens"]
        super().__init__(**data)


class UploadAnnotations(BaseModel):
    class Resource(BaseModel):
        classes: List[str] = Field([], alias="class")
        templates: List[str] = Field([], alias="template")
        attributes: List[str] = Field([], alias="attribute")
        attribute_groups: Optional[List[str]] = Field([], alias="attributeGroup")

    failed_items: List[str] = Field([], alias="failedItems")
    missing_resources: Resource = Field({}, alias="missingResources")


class UploadCustomFieldValues(BaseModel):
    succeeded_items: Optional[List[Any]]
    failed_items: Optional[List[str]]
    error: Optional[Any]


class ServiceResponse(BaseModel):
    status: Optional[int]
    reason: Optional[str]
    content: Optional[Union[bytes, str]]
    data: Optional[Any]
    count: Optional[int] = 0
    _error: Optional[str] = None

    class Config:
        extra = Extra.allow

    def __init__(
        self, response=None, content_type=None, dispatcher: Callable = None, data=None
    ):
        if response is None:
            super().__init__(data=data, status=200)
            return
        data = {
            "status": response.status_code,
            "reason": response.reason,
            "content": response.content,
        }
        try:
            response_json = response.json()
        except Exception:
            response_json = dict()
        if not response.ok:
            error = response_json.get("error")
            if not error:
                error = response_json.get("errors", "Unknown Error")
            data["_error"] = error
            super().__init__(**data)
            return
        if dispatcher:
            _data = response_json
            response_json = dispatcher(_data)
            data.update(_data)
        try:
            if isinstance(response_json, dict):
                data["count"] = response_json.get("count", None)

            if content_type and content_type is not self.__class__:
                data["data"] = parse_obj_as(content_type, response_json)
            else:
                data["data"] = response_json
        except Exception:
            data["data"] = {}

        super().__init__(**data)

    @property
    def status_code(self):
        return self.status

    @property
    def ok(self):
        if self.status:
            return 199 < self.status < 300
        return False

    @property
    def error(self):
        if self._error:
            return self._error
        default_message = self.reason if self.reason else "Unknown Error"
        if isinstance(self.data, dict) and "error" in self.data:
            return self.data.get("error", default_message)
        else:
            return getattr(self.data, "error", default_message)

    def set_error(self, value: Union[dict, str]):
        if isinstance(value, dict) and "error" in value:
            self._error = value["error"]
        self._error = value


class TeamResponse(ServiceResponse):
    data: entities.TeamEntity = None


class ModelListResponse(ServiceResponse):
    data: List[entities.AnnotationClassEntity] = None


class IntegrationResponse(ServiceResponse):
    data: List[entities.IntegrationEntity] = None


class AnnotationClassListResponse(ServiceResponse):
    data: List[entities.AnnotationClassEntity] = None


class SubsetListResponse(ServiceResponse):
    data: List[entities.SubSetEntity] = None


class SubsetResponse(ServiceResponse):
    data: entities.SubSetEntity = None


class DownloadMLModelAuthDataResponse(ServiceResponse):
    data: DownloadMLModelAuthData = None


class UploadAnnotationsResponse(ServiceResponse):
    data: Optional[UploadAnnotations] = None


class UploadAnnotationAuthDataResponse(ServiceResponse):
    data: UploadAnnotationAuthData = None


class UploadCustomFieldValuesResponse(ServiceResponse):
    data: UploadCustomFieldValues = None


class UserLimitsResponse(ServiceResponse):
    data: UserLimits = None


class ItemListResponse(ServiceResponse):
    data: List[entities.BaseItemEntity] = None


class FolderResponse(ServiceResponse):
    data: entities.FolderEntity = None


class FolderListResponse(ServiceResponse):
    data: List[entities.FolderEntity] = None


class ProjectResponse(ServiceResponse):
    data: entities.ProjectEntity = None


class ProjectListResponse(ServiceResponse):
    data: List[entities.ProjectEntity] = None


class SettingsListResponse(ServiceResponse):
    data: List[entities.SettingEntity] = None
