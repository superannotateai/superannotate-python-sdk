from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Iterable
from typing import List


class BaseEntity(ABC):
    def __init__(self, uuid: Any = None):
        self._uuid = uuid

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value: Any):
        self._uuid = value

    @abstractmethod
    def to_dict(self):
        raise NotImplementedError


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


class ProjectEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        team_id: int = None,
        name: str = None,
        project_type: int = None,
        description: str = None,
        status: int = None,
        folder_id: int = None,
        upload_state: int = None,
        users: Iterable = (),
        contributors: List = None,
        settings: List = None,
        annotation_classes: List = None,
        workflow: List = None,
        root_folder_completed_images_count: int = None,
    ):
        super().__init__(uuid)
        self.team_id = team_id
        self.name = name
        self.project_type = project_type
        self.description = description
        self.status = status
        self.folder_id = folder_id
        self.upload_state = upload_state
        self.users = users
        self.contributors = contributors
        self.settings = settings
        self.annotation_classes = annotation_classes
        self.workflow = workflow
        self.root_folder_completed_images_count = root_folder_completed_images_count

    def __copy__(self):
        return ProjectEntity(
            team_id=self.team_id,
            name=self.name,
            project_type=self.project_type,
            description=self.description,
            status=self.status,
            folder_id=self.folder_id,
            users=self.users,
            upload_state=self.upload_state,
        )

    def to_dict(self):
        return {
            "id": self.uuid,
            "team_id": self.team_id,
            "name": self.name,
            "type": self.project_type,
            "description": self.description,
            "status": self.status,
            "folder_id": self.folder_id,
            "upload_state": self.upload_state,
            "users": self.users,
            "rootFolderCompletedImagesCount": self.root_folder_completed_images_count,
        }


class ProjectSettingEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        project_id: int = None,
        attribute: str = None,
        value: Any = None,
    ):
        super().__init__(uuid)
        self.project_id = project_id
        self.attribute = attribute
        self.value = value

    def __copy__(self):
        return ProjectSettingEntity(attribute=self.attribute, value=self.value)

    def to_dict(self):
        return {
            "id": self.uuid,
            "project_id": self.project_id,
            "attribute": self.attribute,
            "value": self.value,
        }


class WorkflowEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        project_id: int = None,
        class_id: int = None,
        step: int = None,
        tool: int = None,
        attribute: Iterable = (),
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


class FolderEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        project_id: int = None,
        parent_id: int = None,
        team_id: int = None,
        name: str = None,
    ):
        super().__init__(uuid)
        self.team_id = team_id
        self.project_id = project_id
        self.name = name
        self.parent_id = parent_id

    def to_dict(self):
        return {
            "id": self.uuid,
            "team_id": self.team_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "project_id": self.project_id,
        }


class ImageInfoEntity(BaseEntity):
    def __init__(
        self, uuid=None, width: float = None, height: float = None,
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
        is_pinned: bool = None,
        meta: ImageInfoEntity = ImageInfoEntity(),
    ):
        super().__init__(uuid)
        self.team_id = team_id
        self.name = name
        self.path = path
        self.project_id = project_id
        self.project_id = project_id
        self.annotation_status_code = annotation_status_code
        self.folder_id = folder_id
        self.annotator_id = annotator_id
        self.annotator_name = annotator_name
        self.is_pinned = is_pinned
        self.meta = meta

    def to_dict(self):
        return {
            "id": self.uuid,
            "team_id": self.team_id,
            "name": self.name,
            "path": self.path,
            "project_id": self.project_id,
            "annotation_status": self.annotation_status_code,
            "folder_id": self.folder_id,
            "annotator_id": self.annotator_id,
            "annotator_name": self.annotator_name,
            "is_pinned": self.is_pinned,
            "meta": self.meta.to_dict(),
        }


class S3FileEntity(BaseEntity):
    def __init__(self, uuid, data, metadata: dict = None):
        super().__init__(uuid)
        self.data = data
        self.metadata = metadata

    def to_dict(self):
        return {"uuid": self.uuid, "bytes": self.data, "metadata": self.metadata}


class AnnotationClassEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        color: str = None,
        count: int = None,
        name: str = None,
        project_id: int = None,
        attribute_groups: Iterable = (),
    ):
        super().__init__(uuid)
        self.color = color
        self.count = count
        self.name = name
        self.project_id = project_id
        self.attribute_groups = attribute_groups

    def __copy__(self):
        return AnnotationClassEntity(
            color=self.color,
            count=self.count,
            name=self.name,
            attribute_groups=self.attribute_groups,
        )

    def to_dict(self):
        return {
            "id": self.uuid,
            "color": self.color,
            "count": self.count,
            "name": self.name,
            "project_id": self.project_id,
            "attribute_groups": self.attribute_groups,
        }


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
    ):
        super().__init__(uuid)
        self.name = name
        self.description = description
        self.team_type = team_type
        self.user_role = user_role
        self.is_default = is_default
        self.users = users
        self.pending_invitations = pending_invitations

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
        }


class AttachmentEntity(BaseEntity):
    def __init__(
        self, uuid: int = None, path: str = None,
    ):
        super().__init__(uuid=uuid)
        self.path = path

    def to_dict(self):
        return {"name": self.uuid, "path": self.path}
