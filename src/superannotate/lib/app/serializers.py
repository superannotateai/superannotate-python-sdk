from abc import ABC
from typing import Any
from typing import List
from typing import Set
from typing import Union

import superannotate.lib.core as constance
from pydantic import BaseModel
from superannotate.lib.core.entities import BaseEntity
from superannotate.lib.core.entities import ImageEntity
from superannotate.lib.core.entities import ProjectEntity


class BaseSerializer(ABC):
    def __init__(self, entity: BaseEntity):
        self._entity = entity

    @staticmethod
    def _fill_enum_values(data: dict):
        if isinstance(data, dict):
            for key, value in data.items():
                if hasattr(value, "_type") and value._type == "titled_enum":
                    data[key] = value.__doc__
        return data

    def serialize(
        self, fields: List[str] = None, by_alias: bool = True, flat: bool = False
    ):
        return self._fill_enum_values(
            self._serialize(self._entity, fields, by_alias, flat)
        )

    def serialize_item(
        self,
        data: Any,
        fields: Union[List[str], Set[str]] = None,
        by_alias: bool = False,
        flat: bool = False,
    ):
        return self._fill_enum_values(self._serialize(data, fields, by_alias, flat))

    @staticmethod
    def _serialize(
        entity: Any,
        fields: List[str] = None,
        by_alias: bool = False,
        flat: bool = False,
    ):
        if isinstance(entity, dict):
            return entity
        if isinstance(entity, BaseModel):
            if fields:
                fields = set(fields)
                if len(fields) == 1:
                    if flat:
                        return entity.dict(include=fields, by_alias=by_alias)[
                            next(iter(fields))
                        ]
                    return entity.dict(include=fields, by_alias=by_alias)
                return entity.dict(include=fields, by_alias=by_alias)
            return entity.dict(by_alias=by_alias)
        return entity.to_dict()

    @classmethod
    def serialize_iterable(
        cls,
        data: List[Any],
        fields: Union[List[str], Set[str]] = None,
        by_alias: bool = False,
        flat: bool = False,
    ) -> List[Any]:
        serialized_data = []
        for i in data:
            serialized_data.append(
                cls._fill_enum_values(cls._serialize(i, fields, by_alias, flat))
            )
        return serialized_data


class UserSerializer(BaseSerializer):
    def serialize(self):
        data = super().serialize()
        data["user_role"] = constance.UserRole[data["user_role"]].name
        return data


class TeamSerializer(BaseSerializer):
    def serialize(self):
        data = super().serialize()
        users = []
        for user in data["users"]:
            user["user_role"] = constance.UserRole.get_name(user["user_role"])
            users.append(user)
        data["users"] = users
        for user in data["pending_invitations"]:
            user["user_role"] = constance.UserRole.get_name(user["user_role"])
        return data


class ProjectSerializer(BaseSerializer):
    def serialize(self):
        data = super().serialize()
        data["type"] = constance.ProjectType.get_name(data["type"])
        if data.get("status"):
            data["status"] = constance.ProjectStatus.get_name(data["status"])
        else:
            data["status"] = "Undefined"
        if data.get("upload_state"):
            data["upload_state"] = constance.UploadState(data["upload_state"]).name
        if data.get("users"):
            for contributor in data["users"]:
                contributor["user_role"] = constance.UserRole.get_name(
                    contributor["user_role"]
                )
        return data


class FolderSerializer(BaseSerializer):
    def serialize(self):
        data = super().serialize()
        del data["is_root"]
        return data


class ImageSerializer(BaseSerializer):
    def serialize(self):
        data = super().serialize()
        data["annotation_status"] = constance.AnnotationStatus.get_name(
            data["annotation_status"]
        )
        return data

    def serialize_by_project(self, project: ProjectEntity):
        data = super().serialize()
        data = {
            "name": data.get("name"),
            "path": data.get("path"),
            "annotation_status": data.get("annotation_status"),
            "prediction_status": data.get("prediction_status"),
            "segmentation_status": data.get("segmentation_status"),
            "approval_status": data.get("approval_status"),
            "is_pinned": data.get("is_pinned"),
            "annotator_name": data.get("annotator_name"),
            "qa_name": data.get("qa_name"),
            "entropy_value": data.get("entropy_value"),
            "createdAt": data.get("createdAt"),
            "updatedAt": data.get("updatedAt"),
        }

        data["annotation_status"] = constance.AnnotationStatus.get_name(
            data["annotation_status"]
        )

        if project.upload_state == constance.UploadState.EXTERNAL.value:
            data["prediction_status"] = None
            data["segmentation_status"] = None
        else:
            if project.project_type == constance.ProjectType.VECTOR.value:
                data["prediction_status"] = constance.SegmentationStatus.get_name(
                    data["prediction_status"]
                )
                data["segmentation_status"] = None
            if project.project_type == constance.ProjectType.PIXEL.value:
                data["prediction_status"] = constance.SegmentationStatus.get_name(
                    data["prediction_status"]
                )
                data["segmentation_status"] = constance.SegmentationStatus.get_name(
                    data["segmentation_status"]
                )
            data["path"] = None
        return data

    @staticmethod
    def deserialize(data):
        if isinstance(data, list):
            return [ImageEntity(**image) for image in data]
        return ImageEntity(**data)


class SettingsSerializer(BaseSerializer):
    def serialize(self):
        data = super().serialize()
        if data["attribute"] == "ImageQuality":
            data["value"] = constance.ImageQuality.get_name(data["value"])
        return data
