from abc import ABC

import superannotate.lib.core as constance
from superannotate.lib.core.entities import BaseEntity
from superannotate.lib.core.entities import ImageEntity
from superannotate.lib.core.entities import ProjectEntity


class BaseSerializers(ABC):
    def __init__(self, entity: BaseEntity):
        self._entity = entity

    def serialize(self):
        if isinstance(self._entity, dict):
            return self._entity
        return self._entity.to_dict()


class UserSerializer(BaseSerializers):
    def serialize(self):
        data = super().serialize()
        data["user_role"] = constance.UserRole[data["user_role"]].name
        return data


class TeamSerializer(BaseSerializers):
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


class ProjectSerializer(BaseSerializers):
    def serialize(self):
        data = super().serialize()
        data["type"] = constance.ProjectType.get_name(data["type"])
        if data.get("upload_state"):
            data["upload_state"] = constance.UploadState(data["upload_state"]).name
        if data.get("users"):
            for contributor in data["users"]:
                contributor["user_role"] = constance.UserRole.get_name(
                    contributor["user_role"]
                )
        return data


class ImageSerializer(BaseSerializers):
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


class SettingsSerializer(BaseSerializers):
    def serialize(self):
        data = super().serialize()
        if data["attribute"] == "ImageQuality":
            data["value"] = constance.ImageQuality.get_name(data["value"])
        return data
