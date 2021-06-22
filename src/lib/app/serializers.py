from abc import ABC

import src.lib.core as constance
from lib.core.entities import BaseEntity


class BaseSerializers(ABC):
    def __init__(self, entity: BaseEntity):
        self._entity = entity

    def serialize(self):
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
            user["user_role"] = constance.UserRole(data["user_role"]).name
            users.append(user)
        data["users"] = users
        for user in data["pending_invitations"]:
            user["user_role"] = constance.UserRole(data["user_role"]).name
        return data


class ProjectSerializer(BaseSerializers):
    def serialize(self):
        data = super().serialize()
        data["type"] = constance.ProjectType(data["type"]).name
        if data.get("upload_state"):
            data["upload_state"] = constance.UploadState(data["upload_state"]).name

        return data
