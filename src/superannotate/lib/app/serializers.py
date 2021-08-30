from abc import ABC

import superannotate.lib.core as constance
from superannotate.lib.core.entities import BaseEntity
from superannotate.lib.core.entities import ImageEntity


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
