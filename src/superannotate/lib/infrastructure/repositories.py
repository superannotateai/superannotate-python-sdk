import io
from typing import List

from lib.core.conditions import Condition
from lib.core.entities import ProjectEntity
from lib.core.entities import S3FileEntity
from lib.core.repositories import BaseS3Repository


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
