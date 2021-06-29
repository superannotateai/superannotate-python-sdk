import configparser
import io
import os
from typing import List
from typing import Optional

import boto3
import src.lib.core as constance
from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ
from src.lib.core.entities import AnnotationClassEntity
from src.lib.core.entities import ConfigEntity
from src.lib.core.entities import FolderEntity
from src.lib.core.entities import ImageEntity
from src.lib.core.entities import ImageFileEntity
from src.lib.core.entities import ProjectEntity
from src.lib.core.entities import ProjectSettingEntity
from src.lib.core.entities import TeamEntity
from src.lib.core.entities import UserEntity
from src.lib.core.entities import WorkflowEntity
from src.lib.core.repositories import BaseManageableRepository
from src.lib.core.repositories import BaseProjectRelatedManageableRepository
from src.lib.core.repositories import BaseReadOnlyRepository
from src.lib.infrastructure.services import SuperannotateBackendService


class ConfigRepository(BaseManageableRepository):
    DEFAULT_SECTION = "default"

    @staticmethod
    def _create_config(path):
        """
        Create a config file
        """
        config = configparser.ConfigParser()
        config.add_section("default")
        with open(path, "w") as config_file:
            config.write(config_file)
        return config

    def _get_config(self, path):
        config = None
        if not os.path.exists(path):
            return config
        config = configparser.ConfigParser()
        config.read(constance.CONFIG_FILE_LOCATION)
        return config

    def get_one(self, uuid: str) -> Optional[ConfigEntity]:
        config = self._get_config(constance.CONFIG_FILE_LOCATION)
        if not config:
            return None
        try:
            return ConfigEntity(uuid=uuid, value=config[self.DEFAULT_SECTION][uuid])
        except KeyError:
            return None

    def get_all(self, condition: Condition = None) -> List[ConfigEntity]:
        config = self._get_config(constance.CONFIG_FILE_LOCATION)
        return [
            ConfigEntity(uuid, value)
            for uuid, value in config.items(self.DEFAULT_SECTION)
        ]

    def insert(self, entity: ConfigEntity) -> ConfigEntity:
        config = self._get_config(constance.CONFIG_FILE_LOCATION)
        if not config:
            config = self._create_config(constance.CONFIG_FILE_LOCATION)
        config.set("default", entity.uuid, entity.value)
        with open(constance.CONFIG_FILE_LOCATION, "w") as config_file:
            config.write(config_file)
        return entity

    def update(self, entity: ConfigEntity):
        self.insert(entity)

    def delete(self, uuid: str):
        config = self._get_config(constance.CONFIG_FILE_LOCATION)
        config.remove_option("default", uuid)
        with open(constance.CONFIG_FILE_LOCATION, "rw+") as config_file:
            config.write(config_file)


class ProjectRepository(BaseManageableRepository):
    def __init__(self, service: SuperannotateBackendService):
        self._service = service

    def get_one(self, uuid: int, team_id: int) -> ProjectEntity:
        return self.dict2entity(self._service.get_project(uuid, team_id))

    def get_all(self, condition: Condition = None) -> List[ProjectEntity]:
        condition = condition.build_query() if condition else None
        return [
            self.dict2entity(project_data)
            for project_data in self._service.get_projects(condition)
        ]

    def insert(self, entity: ProjectEntity) -> ProjectEntity:
        project_data = self._drop_nones(entity.to_dict())
        result = self._service.create_project(project_data)
        return self.dict2entity(result)

    def update(self, entity: ProjectEntity):
        condition = Condition("team_id", entity.team_id, EQ)
        self._service.update_project(
            entity.to_dict(), query_string=condition.build_query()
        )

    def delete(self, entity: ProjectEntity):
        team_id = entity.team_id
        uuid = entity.uuid
        condition = Condition("team_id", team_id, EQ)
        self._service.delete_project(uuid=uuid, query_string=condition.build_query())

    @staticmethod
    def dict2entity(data: dict):
        return ProjectEntity(
            uuid=data["id"],
            team_id=data["team_id"],
            name=data["name"],
            project_type=data["type"],
            status=data["status"],
            description=data["description"],
            folder_id=data.get("folder_id"),
            users=data.get("users", ()),
        )


class S3Repository(BaseManageableRepository):
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        session_token: str,
        bucket: str,
        region: str = None,
    ):
        self._session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
        )

        self._resource = self._session.resource("s3")
        self._bucket = bucket
        self.bucket = self._resource.Bucket(bucket)

    def get_one(self, uuid: str) -> ImageFileEntity:
        file = io.BytesIO()
        self._resource.Object(self._bucket, uuid).download_fileobj(file)
        return ImageFileEntity(uuid=uuid, data=file)

    def insert(self, entity: ImageFileEntity) -> ImageFileEntity:
        data = {"Key": entity.uuid, "Body": entity.data}
        if entity.metadata:
            temp = entity.metadata
            for k in temp:
                temp[k] = str(temp[k])
            data["Metadata"] = temp
        self.bucket.put_object(**data)
        return entity

    def update(self, entity: ProjectEntity):
        self._service.update_project(entity.to_dict())

    def delete(self, uuid: int):
        self._service.delete_project(uuid)

    def get_all(self, condition: Condition = None) -> List[ProjectEntity]:
        pass


class ProjectSettingsRepository(BaseProjectRelatedManageableRepository):
    def get_one(self, uuid: int) -> ProjectEntity:
        raise NotImplementedError

    def get_all(
        self, condition: Optional[Condition] = None
    ) -> List[ProjectSettingEntity]:
        data = self._service.get_project_settings(
            self._project.uuid, self._project.team_id
        )
        return [self.dict2entity(setting) for setting in data]

    def insert(self, entity: ProjectSettingEntity) -> ProjectSettingEntity:
        res = self._service.set_project_settings(
            entity.project_id, self._project.team_id, entity.to_dict()
        )
        return self.dict2entity(res[0])

    def delete(self, uuid: int):
        raise NotImplementedError

    def update(self, entity: ProjectSettingEntity):
        raise NotImplementedError

    @staticmethod
    def dict2entity(data: dict):
        return ProjectSettingEntity(
            uuid=data["id"],
            project_id=data["project_id"],
            attribute=data["attribute"],
            value=data["value"],
        )


class WorkflowRepository(BaseProjectRelatedManageableRepository):
    def get_one(self, uuid: int) -> WorkflowEntity:
        raise NotImplementedError

    def get_all(self, condition: Optional[Condition] = None) -> List[WorkflowEntity]:
        data = self._service.get_project_workflows(
            self._project.uuid, self._project.team_id
        )
        return [self.dict2entity(setting) for setting in data]

    def insert(self, entity: WorkflowEntity) -> WorkflowEntity:
        data = entity.to_dict()
        del data["project_id"]
        del data["attribute"]
        res = self._service.set_project_workflow(
            entity.project_id, self._project.team_id, self._drop_nones(data)
        )
        return self.dict2entity(res[0])

    def delete(self, uuid: int):
        raise NotImplementedError

    def update(self, entity: WorkflowEntity):
        raise NotImplementedError

    @staticmethod
    def dict2entity(data: dict):
        return WorkflowEntity(
            uuid=data["id"],
            project_id=data["project_id"],
            class_id=data["class_id"],
            step=data["step"],
            tool=data["tool"],
            attribute=data.get("attribute"),
        )


class FolderRepository(BaseProjectRelatedManageableRepository):
    def get_one(self, uuid: Condition) -> FolderEntity:
        condition = uuid.build_query()
        data = self._service.get_folder(condition)
        return self.dict2entity(data)

    def get_all(self, condition: Optional[Condition] = None) -> List[FolderEntity]:
        condition = (
            condition
            & Condition("project_id", self._project.uuid, EQ)
            & Condition("team_id", self._project.team_id, EQ)
        )
        condition = condition.build_query()
        data = self._service.get_folders(condition)
        return [self.dict2entity(image) for image in data]

    def insert(self, entity: FolderEntity) -> FolderEntity:
        res = self._service.create_folder(
            project_id=entity.project_id,
            team_id=entity.team_id,
            folder_name=entity.name,
        )
        return self.dict2entity(res)

    def update(self, entity: FolderEntity):
        self._service.update_folder(
            self._project.uuid, self._project.team_id, entity.to_dict()
        )

    def delete(self, uuid: int):
        self._service.delete_folders(self._project.uuid, self._project.team_id, [uuid])

    @staticmethod
    def dict2entity(data: dict):
        return FolderEntity(
            uuid=data["id"],
            team_id=data["team_id"],
            project_id=data["project_id"],
            name=data["name"],
        )


class AnnotationClassRepository(BaseManageableRepository):
    def __init__(self, service: SuperannotateBackendService, project: ProjectEntity):
        self._service = service
        self.project = project

    def get_one(self, uuid: Condition) -> AnnotationClassEntity:
        raise NotImplementedError

    def get_all(
        self, condition: Optional[Condition] = None
    ) -> List[AnnotationClassEntity]:
        res = self._service.get_annotation_classes(
            self.project.uuid, self.project.team_id
        )
        return [self.dict2entity(data) for data in res]

    def insert(self, entity: AnnotationClassEntity):
        res = self._service.set_annotation_classes(
            entity.project_id, self.project.team_id, [entity.to_dict()]
        )
        return self.dict2entity(res[0])

    def delete(self, uuid: int):
        raise NotImplementedError

    def update(self, entity: AnnotationClassEntity):
        raise NotImplementedError

    @staticmethod
    def dict2entity(data: dict):
        return AnnotationClassEntity(
            uuid=data["id"],
            project_id=data["project_id"],
            name=data["name"],
            count=data["count"],
            color=data["color"],
            attribute_groups=data["attribute_groups"],
        )


class ImageRepositroy(BaseManageableRepository):
    def __init__(self, service: SuperannotateBackendService):
        self._service = service

    def get_one(self, uuid: int) -> ImageEntity:
        raise NotImplementedError

    def get_all(self, condition: Optional[Condition] = None) -> List[ImageEntity]:
        images = self._service.get_images(condition.build_query())
        return [self.dict2entity(image) for image in images]

    def insert(self, entity: ImageEntity) -> ImageEntity:
        raise NotImplementedError

    def delete(self, uuid: int):
        raise NotImplementedError

    def update(self, entity: ImageEntity):
        raise NotImplementedError

    @staticmethod
    def dict2entity(data: dict):
        return ImageEntity(
            uuid=data["id"],
            name=data["name"],
            path=data["path"],
            project_id=data["project_id"],
            team_id=data["team_id"],
            annotation_status_code=data["annotation_status"],
            folder_id=data["folder_id"],
            annotator_id=data["annotator_id"],
            annotator_name=data["annotator_name"],
        )


class UserRepository(BaseReadOnlyRepository):
    @staticmethod
    def dict2entity(data: dict):
        return UserEntity(
            uuid=data["id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            picture=data["picture"],
            user_role=data["user_role"],
        )


class TeamRepository(BaseReadOnlyRepository):
    def __init__(self, service: SuperannotateBackendService):
        self._service = service

    def get_one(self, uuid: int) -> Optional[TeamEntity]:
        res = self._service.get_team(team_id=uuid)
        return self.dict2entity(res)

    def get_all(self, condition: Optional[Condition] = None) -> List[TeamEntity]:
        raise NotImplementedError

    @staticmethod
    def dict2entity(data: dict):
        return TeamEntity(
            uuid=data["id"],
            name=data["name"],
            description=data["description"],
            team_type=data["type"],
            user_role=data["user_role"],
            is_default=data["is_default"],
            users=[UserRepository.dict2entity(user) for user in data["users"]],
            pending_invitations=data["pending_invitations"],
        )
