import io
import json
import os
from os.path import expanduser
from typing import List
from typing import Optional

import lib.core as constance
from lib.core.conditions import Condition
from lib.core.entities import ConfigEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import S3FileEntity
from lib.core.repositories import BaseManageableRepository
from lib.core.repositories import BaseS3Repository


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
