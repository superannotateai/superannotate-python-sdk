from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from lib.core import entities
from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field


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
    content: Optional[Union[bytes, str]] = None
    data: Optional[Any] = None
    count: Optional[int] = 0
    _error: Optional[str] = None

    class Config:
        extra = Extra.allow

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
        return self.data

    def set_error(self, value: Union[dict, str]):
        if isinstance(value, dict) and "error" in value:
            self._error = value["error"]
        self._error = value

    def __str__(self):
        return f"Status: {self.status_code}, Error {self.error}"


class ImageResponse(ServiceResponse):
    data: entities.ImageEntity = None


class VideoResponse(ServiceResponse):
    data: entities.VideoEntity = None


class DocumentResponse(ServiceResponse):
    data: entities.DocumentEntity = None


class TiledResponse(ServiceResponse):
    data: entities.TiledEntity = None


class ClassificationResponse(ServiceResponse):
    data: entities.ClassificationEntity = None


class PointCloudResponse(ServiceResponse):
    data: entities.PointCloudEntity = None


class TeamResponse(ServiceResponse):
    data: entities.TeamEntity = None


class ModelListResponse(ServiceResponse):
    data: List[entities.AnnotationClassEntity] = None


class _IntegrationResponse(ServiceResponse):
    integrations: List[entities.IntegrationEntity] = []


class IntegrationListResponse(ServiceResponse):
    data: _IntegrationResponse


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
