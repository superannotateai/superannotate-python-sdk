import io
import json
import os
from os.path import expanduser
from typing import List
from typing import Optional

import lib.core as constance
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AnnotationClassEntity
from lib.core.entities import ConfigEntity
from lib.core.entities import Entity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import IntegrationEntity
from lib.core.entities import MLModelEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import ProjectSettingEntity
from lib.core.entities import S3FileEntity
from lib.core.entities import TeamEntity
from lib.core.entities import UserEntity
from lib.core.entities import WorkflowEntity
from lib.core.enums import ClassTypeEnum
from lib.core.enums import ImageQuality
from lib.core.exceptions import AppException
from lib.core.repositories import BaseManageableRepository
from lib.core.repositories import BaseProjectRelatedManageableRepository
from lib.core.repositories import BaseReadOnlyRepository
from lib.core.repositories import BaseS3Repository
from lib.infrastructure.services import SuperannotateBackendService
from pydantic import parse_obj_as


class ConfigRepository(BaseManageableRepository):
    def __init__(self, config_path: str = constance.CONFIG_FILE_LOCATION):
        self._config_path = f"{config_path}"

    @property
    def config_path(self):
        return expanduser(self._config_path)

    def _create_config(self):
        """
        Create a config file
        """
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        open(self.config_path, "w").close()
        return {}

    def _get_config(self) -> Optional[dict]:
        if os.path.exists(self.config_path):
            return json.load(open(self.config_path))

    def get_one(self, uuid: str) -> Optional[ConfigEntity]:
        config = self._get_config()
        if not config:
            return None
        try:
            return ConfigEntity(uuid=uuid, value=config.get(uuid))
        except KeyError:
            return None

    def get_all(self, condition: Condition = None) -> List[ConfigEntity]:
        config = self._get_config()
        if config:
            return [ConfigEntity(uuid, value) for uuid, value in config.items()]

    def insert(self, entity: ConfigEntity) -> ConfigEntity:
        config = self._get_config()
        if not config:
            config = self._create_config()
        config[entity.uuid] = entity.value
        with open(self._config_path, "w") as config_file:
            config_file.write(json.dumps(config, sort_keys=True, indent=4))
        return entity

    def update(self, entity: ConfigEntity):
        self.insert(entity)

    def delete(self, uuid: str):
        config = self._get_config()
        del config["uuid"]
        with open(constance.CONFIG_FILE_LOCATION, "rw+") as config_file:
            config_file.write(json.dumps(config, sort_keys=True, indent=4))


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
        result = self._service.update_project(
            entity.to_dict(), query_string=condition.build_query()
        )
        return self.dict2entity(result)

    def delete(self, entity: ProjectEntity):
        team_id = entity.team_id
        uuid = entity.uuid
        condition = Condition("team_id", team_id, EQ)
        return self._service.delete_project(
            uuid=uuid, query_string=condition.build_query()
        )

    @staticmethod
    def dict2entity(data: dict) -> ProjectEntity:
        try:
            return ProjectEntity(
                uuid=data["id"],
                team_id=data["team_id"],
                name=data["name"],
                project_type=data["type"],
                status=data.get("status"),
                instructions_link=data.get("instructions_link"),
                entropy_status=data.get("entropy_status"),
                sharing_status=data.get("sharing_status"),
                creator_id=data["creator_id"],
                upload_state=data["upload_state"],
                description=data.get("description"),
                sync_status=data.get("sync_status"),
                folder_id=data.get("folder_id"),
                users=data.get("users", ()),
                unverified_users=data.get("unverified_users", ()),
                completed_images_count=data.get("completedImagesCount"),
                root_folder_completed_images_count=data.get(
                    "rootFolderCompletedImagesCount"
                ),
                createdAt=data.get("createdAt"),
                updatedAt=data.get("updatedAt"),
            )
        except KeyError:
            raise AppException("Cant serialize project data")


class S3Repository(BaseS3Repository):
    def get_one(self, uuid: str) -> S3FileEntity:
        file = io.BytesIO()
        self._resource.Object(self._bucket, uuid).download_fileobj(file)
        return S3FileEntity(uuid=uuid, data=file)

    def insert(self, entity: S3FileEntity) -> S3FileEntity:
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
        if data:
            return [self.dict2entity(setting) for setting in data]
        return []

    def insert(self, entity: ProjectSettingEntity) -> ProjectSettingEntity:
        entity = entity.to_dict()
        entity.pop("key", None)
        res = self._service.set_project_settings(
            self._project.uuid, self._project.team_id, [entity]
        )
        return self.dict2entity(res[0])

    def delete(self, uuid: int):
        raise NotImplementedError

    def update(self, entity: ProjectSettingEntity):
        if entity.attribute == "ImageQuality" and isinstance(entity.value, str):
            entity.value = ImageQuality.get_value(entity.value)
        self._service.set_project_settings(
            self._project.uuid, self._project.team_id, [entity.to_dict()]
        )
        return entity

    @staticmethod
    def dict2entity(data: dict) -> ProjectSettingEntity:
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
    def dict2entity(data: dict) -> WorkflowEntity:
        return WorkflowEntity(
            uuid=data["id"],
            project_id=data["project_id"],
            class_id=data["class_id"],
            step=data["step"],
            tool=data["tool"],
            attribute=data.get("attribute", []),
        )


class FolderRepository(BaseManageableRepository):
    def __init__(self, service: SuperannotateBackendService):
        self._service = service

    def get_one(self, uuid: Condition) -> FolderEntity:
        condition = uuid.build_query()
        data = self._service.get_folder(condition)
        if data:
            return self.dict2entity(data)

    def get_all(self, condition: Optional[Condition] = None) -> List[FolderEntity]:
        condition = condition.build_query() if condition else None
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
        project_id = entity.project_id
        team_id = entity.team_id
        response = self._service.update_folder(project_id, team_id, entity.to_dict())
        if response:
            return self.dict2entity(response)

    def delete(self, entity: FolderEntity):
        return self._service.delete_folders(
            entity.project_id, entity.team_id, [entity.uuid]
        )

    def bulk_delete(self, entities: List[FolderEntity]):
        entity = entities[0]
        ids = [entity.uuid for entity in entities]
        return self._service.delete_folders(entity.project_id, entity.team_id, ids)

    @staticmethod
    def dict2entity(data: dict) -> FolderEntity:
        try:
            return FolderEntity(
                uuid=data["id"],
                is_root=bool(data["is_root"]),
                team_id=data["team_id"],
                project_id=data["project_id"],
                name=data["name"],
                folder_users=data.get("folder_users"),
            )
        except KeyError:
            raise AppException("Cant serialize folder data")


class AnnotationClassRepository(BaseManageableRepository):
    def __init__(self, service: SuperannotateBackendService, project: ProjectEntity):
        self._service = service
        self.project = project

    def get_one(self, uuid: Condition) -> AnnotationClassEntity:
        raise NotImplementedError

    def get_all(
            self, condition: Optional[Condition] = None
    ) -> List[AnnotationClassEntity]:
        query = condition.build_query() if condition else None
        data = self._service.get_annotation_classes(
            self.project.uuid, self.project.team_id, query
        )
        if data:
            return [self.dict2entity(data) for data in data]
        return []

    def insert(self, entity: AnnotationClassEntity):
        res = self._service.set_annotation_classes(
            self.project.uuid, self.project.team_id, [entity]
        )
        if "error" in res:
            raise AppException(res["error"])
        return self.dict2entity(res[0])

    def delete(self, uuid: int):
        self._service.delete_annotation_class(
            team_id=self.project.team_id,
            project_id=self.project.uuid,
            annotation_class_id=uuid,
        )

    def bulk_insert(self, entities: List[AnnotationClassEntity]):
        res = self._service.set_annotation_classes(
            self.project.uuid, self.project.team_id, entities
        )
        if "error" in res:
            raise AppException(res["error"])

        return [self.dict2entity(i) for i in res]

    def update(self, entity: AnnotationClassEntity):
        raise NotImplementedError

    @staticmethod
    def dict2entity(data: dict) -> AnnotationClassEntity:
        return AnnotationClassEntity(
            id=data["id"],
            project_id=data["project_id"],
            name=data["name"],
            count=data["count"],
            color=data["color"],
            createdAt=data["createdAt"],
            updatedAt=data["updatedAt"],
            attribute_groups=data["attribute_groups"],
            type=ClassTypeEnum.get_name(data.get("type", 1)),
        )


class ImageRepository(BaseManageableRepository):
    def __init__(self, service: SuperannotateBackendService):
        self._service = service

    def get_one(self, uuid: int) -> ImageEntity:
        raise NotImplementedError

    def get_all(self, condition: Optional[Condition] = None) -> List[ImageEntity]:
        images = self._service.get_images(condition.build_query())
        return [self.dict2entity(image) for image in images]

    def insert(self, entity: ImageEntity) -> ImageEntity:
        raise NotImplementedError

    def delete(self, uuid: int, team_id: int, project_id: int):
        self._service.delete_images(
            image_ids=[uuid], team_id=team_id, project_id=project_id
        )

    def update(self, entity: ImageEntity):
        self._service.update_image(
            image_id=entity.uuid,
            project_id=entity.project_id,
            team_id=entity.team_id,
            data=entity.to_dict(),
        )
        return entity

    @staticmethod
    def dict2entity(data: dict) -> ImageEntity:
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
            is_pinned=data.get("is_pinned"),
            created_at=data["createdAt"],
            updated_at=data["updatedAt"],
        )


class UserRepository(BaseReadOnlyRepository):
    @staticmethod
    def dict2entity(data: dict) -> UserEntity:
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
            creator_id=data["creator_id"],
        )


class MLModelRepository(BaseManageableRepository):
    def __init__(self, service: SuperannotateBackendService, team_id: int):
        self._team_id = team_id
        self._service = service

    def get_one(self, uuid: int) -> MLModelEntity:
        raise NotImplementedError

    def get_all(self, condition: Optional[Condition] = None) -> List[MLModelEntity]:
        models = self._service.search_models(condition.build_query())
        return [self.dict2entity(model) for model in models]

    def insert(self, entity: MLModelEntity) -> MLModelEntity:
        data = self._service.start_model_training(self._team_id, entity.to_dict())
        return self.dict2entity(data)

    def delete(self, uuid: int):
        self._service.delete_model(self._team_id, uuid)

    def update(self, entity: MLModelEntity):
        model_data = {k: v for k, v in entity.to_dict().items() if v}
        data = self._service.update_model(
            team_id=self._team_id, model_id=entity.uuid, data=model_data
        )
        return self.dict2entity(data)

    @staticmethod
    def dict2entity(data: dict) -> MLModelEntity:
        return MLModelEntity(
            uuid=data["id"],
            name=data["name"],
            description=data["description"],
            base_model_id=data["base_model_id"],
            model_type=data["type"],
            task=data["task"],
            image_count=data["image_count"],
            path=data["path"],
            config_path=data["config_path"],
            is_global=data["is_global"],
            training_status=data["training_status"],
        )


class IntegrationRepository(BaseReadOnlyRepository):
    def __init__(self, service: SuperannotateBackendService, team_id: int):
        self._service = service
        self._team_id = team_id

    def get_one(self, uuid: int) -> Optional[TeamEntity]:
        raise NotImplementedError

    def get_all(self, condition: Optional[Condition] = None) -> List[IntegrationEntity]:
        return parse_obj_as(
            List[IntegrationEntity], self._service.get_integrations(self._team_id)
        )


class ItemRepository(BaseReadOnlyRepository):
    def __init__(self, service: SuperannotateBackendService):
        self._service = service

    def get_one(self, uuid: Condition) -> Entity:
        items = self._service.list_items(uuid.build_query())
        if len(items) >= 1:
            return Entity(**Entity.map_fields(items[0]))

    def get_all(self, condition: Optional[Condition] = None) -> List[Entity]:
        items = self._service.list_items(condition.build_query())
        return [Entity(**Entity.map_fields(item)) for item in items]
