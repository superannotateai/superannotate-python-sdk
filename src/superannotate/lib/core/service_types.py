from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from lib.core import entities
from lib.core.entities.work_managament import TelemetryScoreEntity
from lib.core.entities.work_managament import WMProjectEntity
from lib.core.entities.work_managament import WMScoreEntity
from lib.core.entities.work_managament import WMUserEntity
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.pydantic_v1 import BaseModel
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field


class Limit(BaseModel):
    max_image_count: Optional[int]
    remaining_image_count: int

    class Config:
        extra = Extra.ignore


class UserLimits(BaseModel):
    user_limit: Optional[Limit]
    project_limit: Limit
    folder_limit: Limit

    class Config:
        extra = Extra.ignore


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


class UploadAnnotations(BaseModel):
    class Resource(BaseModel):
        classes: List[str] = Field([], alias="class")
        templates: List[str] = Field([], alias="template")
        attributes: List[str] = Field([], alias="attribute")
        attribute_groups: Optional[List[str]] = Field([], alias="attributeGroup")

    failed_items: List[str] = Field([], alias="failedItems")
    missing_resources: Resource = Field({}, alias="missingResources")

    class Config:
        extra = Extra.ignore


class UploadCustomFieldValues(BaseModel):
    succeeded_items: Optional[List[Any]]
    failed_items: Optional[List[str]]
    error: Optional[Any]

    class Config:
        extra = Extra.ignore


class ServiceResponse(BaseModel):
    status: Optional[int]
    reason: Optional[str]
    content: Optional[Union[bytes, str]] = None
    res_data: Optional[Any] = None  # response data
    res_error: Optional[Union[str, list, dict]] = None
    count: Optional[int] = 0
    total: Optional[int] = 0

    class Config:
        extra = Extra.allow

    @property
    def total_count(self):
        if self.total:
            return self.total
        return self.count

    @property
    def data(self):
        if self.error:
            raise AppException(self.error)
        return self.res_data

    @data.setter
    def data(self, value):
        self.res_data = value

    @property
    def status_code(self):
        return self.status

    @property
    def ok(self):
        if self.status:
            return 199 < self.status < 300
        return False

    def raise_for_status(self):
        if not self.ok:
            raise AppException(self.error)

    @property
    def error(self):
        if self.res_error:
            return self.res_error
        if not self.ok:
            return self.res_data

    def set_error(self, value: Union[dict, str]):
        if isinstance(value, dict) and "error" in value:
            self.res_error = value["error"]
        self.res_error = value

    def __str__(self):
        return f"Status: {self.status_code}, Error {self.error}"


class BaseItemResponse(ServiceResponse):
    res_data: entities.BaseItemEntity = None


class ImageResponse(ServiceResponse):
    res_data: entities.ImageEntity = None


class VideoResponse(ServiceResponse):
    res_data: entities.VideoEntity = None


class DocumentResponse(ServiceResponse):
    res_data: entities.DocumentEntity = None


class TiledResponse(ServiceResponse):
    res_data: entities.TiledEntity = None


class ClassificationResponse(ServiceResponse):
    res_data: entities.ClassificationEntity = None


class PointCloudResponse(ServiceResponse):
    res_data: entities.PointCloudEntity = None


class TeamResponse(ServiceResponse):
    res_data: entities.TeamEntity = None


class UserResponse(ServiceResponse):
    res_data: entities.UserEntity = None


class ModelListResponse(ServiceResponse):
    res_data: List[entities.AnnotationClassEntity] = None


class _IntegrationResponse(ServiceResponse):
    integrations: List[entities.IntegrationEntity] = []


class IntegrationListResponse(ServiceResponse):
    res_data: _IntegrationResponse


class AnnotationClassListResponse(ServiceResponse):
    res_data: List[entities.AnnotationClassEntity] = None


class SubsetListResponse(ServiceResponse):
    res_data: List[entities.SubSetEntity] = None


class SubsetResponse(ServiceResponse):
    res_data: entities.SubSetEntity = None


class UploadAnnotationsResponse(ServiceResponse):
    res_data: Optional[UploadAnnotations] = None


class UploadAnnotationAuthDataResponse(ServiceResponse):
    res_data: UploadAnnotationAuthData = None


class UploadCustomFieldValuesResponse(ServiceResponse):
    res_data: UploadCustomFieldValues = None


class UserLimitsResponse(ServiceResponse):
    res_data: UserLimits = None


class ItemListResponse(ServiceResponse):
    res_data: List[entities.BaseItemEntity] = None


class FolderResponse(ServiceResponse):
    res_data: entities.FolderEntity = None


class FolderListResponse(ServiceResponse):
    res_data: List[entities.FolderEntity] = None


class ProjectResponse(ServiceResponse):
    res_data: entities.ProjectEntity = None


class ListCategoryResponse(ServiceResponse):
    res_data: List[entities.CategoryEntity] = None


class ListProjectCategoryResponse(ServiceResponse):
    res_data: List[entities.items.ProjectCategoryEntity] = None


class WorkflowResponse(ServiceResponse):
    res_data: entities.WorkflowEntity = None


class WorkflowListResponse(ServiceResponse):
    res_data: List[entities.WorkflowEntity] = None


class ProjectListResponse(ServiceResponse):
    res_data: List[entities.ProjectEntity] = None


class WMProjectListResponse(ServiceResponse):
    res_data: List[WMProjectEntity] = None


class WMUserListResponse(ServiceResponse):
    res_data: List[WMUserEntity] = None


class WMCustomFieldResponse(ServiceResponse):
    res_data: List[entities.CustomFieldEntity] = None


class SettingsListResponse(ServiceResponse):
    res_data: List[entities.SettingEntity] = None


class WMScoreListResponse(ServiceResponse):
    res_data: List[WMScoreEntity] = None


class TelemetryScoreListResponse(ServiceResponse):
    res_data: List[TelemetryScoreEntity] = None


PROJECT_TYPE_RESPONSE_MAP = {
    ProjectType.VECTOR: ImageResponse,
    ProjectType.OTHER: ClassificationResponse,
    ProjectType.VIDEO: VideoResponse,
    ProjectType.TILED: TiledResponse,
    ProjectType.PIXEL: ImageResponse,
    ProjectType.DOCUMENT: DocumentResponse,
    ProjectType.POINT_CLOUD: PointCloudResponse,
    ProjectType.MULTIMODAL: ImageResponse,
}
