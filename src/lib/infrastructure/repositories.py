import configparser
import os
from typing import List

import src.lib.core as constance
from src.lib.core.conditions import Condition
from src.lib.core.entities import ConfigEntity
from src.lib.core.entities import ProjectEntity
from src.lib.core.repositories import BaseManageableRepository
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

    def _get_config(self, path):
        if not os.path.exists(path):
            self._create_config(path)
        config = configparser.ConfigParser()
        config.read(constance.CONFIG_FILE_LOCATION)
        return config

    def get_one(self, uuid: str) -> ConfigEntity:
        config = self._get_config(constance.CONFIG_FILE_LOCATION)
        return ConfigEntity(uuid=uuid, value=config[self.DEFAULT_SECTION][uuid])

    def get_all(self, condition: Condition = None) -> List[ConfigEntity]:
        config = constance.CONFIG_FILE_LOCATION
        return [
            ConfigEntity(uuid, value)
            for uuid, value in config.items(self.DEFAULT_SECTION)
        ]

    def insert(self, entity: ConfigEntity) -> ConfigEntity:
        config = self._get_config(constance.CONFIG_FILE_LOCATION)
        config.set("default", entity.uuid, entity.value)
        with open(constance.CONFIG_FILE_LOCATION, "rw+") as config_file:
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

    def get_one(self, uuid: str) -> ProjectEntity:
        pass

    def get_all(self, condition: Condition = None) -> List[ProjectEntity]:
        condition = condition.build_query() if condition else None
        return [
            self.dict2entity(project_data)
            for project_data in self._service.get_projects(condition)
        ]

    def insert(self, entity: ProjectEntity) -> ProjectEntity:
        project_data = self._service.create_project(entity.to_dict())
        return self.dict2entity(project_data)

    def update(self, entity: ProjectEntity):
        self._service.update_project(entity.to_dict())

    def delete(self, uuid: int):
        self._service.delete_project(uuid)

    @staticmethod
    def dict2entity(data: dict):
        return ProjectEntity(
            uuid=data["id"],
            team_id=data["team_id"],
            name=data["name"],
            project_type=data["type"],
            status=data["status"],
            description=data["description"],
        )
