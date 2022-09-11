from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Iterable
from typing import List

from lib.core.enums import SegmentationStatus


class BaseEntity(ABC):
    def __init__(self, uuid: Any = None):
        self._uuid = uuid

    @property
    def id(self):
        return self._uuid

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value: Any):
        self._uuid = value

    @abstractmethod
    def to_dict(self):
        raise NotImplementedError


class BaseTimedEntity(BaseEntity):
    def __init__(
        self,
        uuid: Any = None,
        createdAt: str = None,
        updatedAt: str = None,
    ):
        super().__init__(uuid)
        self.createdAt = createdAt
        self.updatedAt = updatedAt

    def to_dict(self):
        return {
            "id": self.uuid,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }


class ConfigEntity(BaseEntity):
    def __init__(self, uuid: str, value: str):
        super().__init__(uuid)
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def to_dict(self):
        return {"key": self.uuid, "value": self.value}


class WorkflowEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        project_id: int = None,
        class_id: int = None,
        step: int = None,
        tool: int = None,
        attribute: Iterable = tuple(),
    ):
        super().__init__(uuid)
        self.project_id = project_id
        self.class_id = class_id
        self.step = step
        self.tool = tool
        self.attribute = attribute

    def __copy__(self):
        return WorkflowEntity(step=self.step, tool=self.tool, attribute=self.attribute)

    def to_dict(self):
        return {
            "id": self.uuid,
            "project_id": self.project_id,
            "class_id": self.class_id,
            "step": self.step,
            "tool": self.tool,
            "attribute": self.attribute,
        }


class FolderEntity(BaseTimedEntity):
    def __init__(
        self,
        uuid: int = None,
        createdAt: str = None,
        updatedAt: str = None,
        project_id: int = None,
        parent_id: int = None,
        team_id: int = None,
        is_root: bool = False,
        name: str = None,
        folder_users: List[dict] = None,
    ):
        super().__init__(uuid, createdAt, updatedAt)
        self.team_id = team_id
        self.project_id = project_id
        self.name = name
        self.parent_id = parent_id
        self.is_root = is_root
        self.folder_users = folder_users

    def to_dict(self):
        return {
            **super().to_dict(),
            "id": self.uuid,
            "team_id": self.team_id,
            "is_root": self.is_root,
            "name": self.name,
            "parent_id": self.parent_id,
            "project_id": self.project_id,
            "folder_users": self.folder_users,
        }


class ImageInfoEntity(BaseEntity):
    def __init__(
        self,
        uuid=None,
        width: float = None,
        height: float = None,
    ):
        super().__init__(uuid),
        self.width = width
        self.height = height

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
        }


class ImageEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        name: str = None,
        path: str = None,
        project_id: int = None,
        team_id: int = None,
        annotation_status_code: int = None,
        folder_id: int = None,
        annotator_id: int = None,
        annotator_name: str = None,
        qa_id: str = None,
        qa_name: str = None,
        entropy_value: int = None,
        approval_status: bool = None,
        is_pinned: bool = None,
        segmentation_status: int = SegmentationStatus.NOT_STARTED.value,
        prediction_status: int = SegmentationStatus.NOT_STARTED.value,
        meta: ImageInfoEntity = ImageInfoEntity(),
        created_at: str = None,
        updated_at: str = None,
        **_,
    ):
        super().__init__(uuid)
        self.team_id = team_id
        self.name = name
        self.path = path
        self.project_id = project_id
        self.project_id = project_id
        self.annotation_status_code = annotation_status_code
        self.folder_id = folder_id
        self.qa_id = qa_id
        self.qa_name = qa_name
        self.entropy_value = entropy_value
        self.annotator_id = annotator_id
        self.approval_status = approval_status
        self.annotator_name = annotator_name
        self.is_pinned = is_pinned
        self.segmentation_status = segmentation_status
        self.prediction_status = prediction_status
        self.meta = meta
        self.created_at = created_at
        self.updated_at = updated_at

    @staticmethod
    def from_dict(**kwargs):
        if "id" in kwargs:
            kwargs["uuid"] = kwargs["id"]
            del kwargs["id"]
        if "annotation_status" in kwargs:
            kwargs["annotation_status_code"] = kwargs["annotation_status"]
            del kwargs["annotation_status"]
        if "createdAt" in kwargs:
            kwargs["created_at"] = kwargs["createdAt"]
            del kwargs["createdAt"]
        if "updatedAt" in kwargs:
            kwargs["updated_at"] = kwargs["updatedAt"]
            del kwargs["updatedAt"]
        return ImageEntity(**kwargs)

    def to_dict(self):
        data = {
            "id": self.uuid,
            "team_id": self.team_id,
            "project_id": self.project_id,
            "folder_id": self.folder_id,
            "name": self.name,
            "path": self.path,
            "annotation_status": self.annotation_status_code,
            "prediction_status": self.prediction_status,
            "segmentation_status": self.segmentation_status,
            "approval_status": self.approval_status,
            "is_pinned": self.is_pinned,
            "annotator_id": self.annotator_id,
            "annotator_name": self.annotator_name,
            "qa_id": self.qa_id,
            "qa_name": self.qa_name,
            "entropy_value": self.entropy_value,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "meta": self.meta.to_dict(),
        }
        return {k: v for k, v in data.items() if v is not None}


class S3FileEntity(BaseEntity):
    def __init__(self, uuid, data, metadata: dict = None):
        super().__init__(uuid)
        self.data = data
        self.metadata = metadata

    def to_dict(self):
        return {"uuid": self.uuid, "bytes": self.data, "metadata": self.metadata}


class UserEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        first_name: str = None,
        last_name: str = None,
        email: str = None,
        picture: int = None,
        user_role: int = None,
    ):
        super().__init__(uuid)
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.picture = picture
        self.user_role = user_role

    def to_dict(self):
        return {
            "id": self.uuid,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "picture": self.picture,
            "user_role": self.user_role,
        }


class TeamEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        name: str = None,
        description: str = None,
        team_type: int = None,
        user_role: int = None,
        is_default: bool = None,
        users: List[UserEntity] = None,
        pending_invitations: List = None,
        creator_id: str = None,
    ):
        super().__init__(uuid)
        self.name = name
        self.description = description
        self.team_type = team_type
        self.user_role = user_role
        self.is_default = is_default
        self.users = users
        self.pending_invitations = pending_invitations
        self.creator_id = creator_id

    def to_dict(self):
        return {
            "id": self.uuid,
            "name": self.name,
            "description": self.description,
            "type": self.team_type,
            "user_role": self.user_role,
            "is_default": self.is_default,
            "users": [user.to_dict() for user in self.users],
            "pending_invitations": self.pending_invitations,
            "creator_id": self.creator_id,
        }


class MLModelEntity(BaseTimedEntity):
    def __init__(
        self,
        uuid: int = None,
        team_id: int = None,
        name: str = None,
        createdAt: str = None,
        updatedAt: str = None,
        path: str = None,
        config_path: str = None,
        model_type: int = None,
        description: str = None,
        output_path: str = None,
        task: str = None,
        base_model_id: int = None,
        image_count: int = None,
        training_status: int = None,
        test_folder_ids: List[int] = None,
        train_folder_ids: List[int] = None,
        is_trainable: bool = None,
        is_global: bool = None,
        hyper_parameters: dict = {},
    ):
        super().__init__(uuid, createdAt, updatedAt)
        self.name = name
        self.path = path
        self.team_id = team_id
        self.config_path = config_path
        self.output_path = output_path
        self.model_type = model_type
        self.description = description
        self.task = task
        self.base_model_id = base_model_id
        self.image_count = image_count
        self.training_status = training_status
        self.test_folder_ids = test_folder_ids
        self.train_folder_ids = train_folder_ids
        self.is_trainable = is_trainable
        self.is_global = is_global
        self.hyper_parameters = hyper_parameters

    def to_dict(self):
        return {
            **super().to_dict(),
            "name": self.name,
            "team_id": self.team_id,
            "description": self.description,
            "task": self.task,
            "project_type": self.model_type,
            "path": self.path,
            "config_path": self.config_path,
            "output_path": self.output_path,
            "base_model_id": self.base_model_id,
            "image_count": self.image_count,
            "training_status": self.training_status,
            "test_folder_ids": self.test_folder_ids,
            "train_folder_ids": self.train_folder_ids,
            "is_trainable": self.is_trainable,
            "is_global": self.is_global,
            **self.hyper_parameters,
        }
