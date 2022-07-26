from abc import ABC
from typing import Any
from typing import List
from typing import Set
from typing import Union

import superannotate.lib.core as constance
from pydantic import BaseModel
from superannotate.lib.core.entities import BaseEntity


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
        self,
        fields: List[str] = None,
        by_alias: bool = True,
        flat: bool = False,
        exclude: Set[str] = None,
    ):
        return self._fill_enum_values(
            self._serialize(self._entity, fields, by_alias, flat, exclude=exclude)
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
        exclude: Set[str] = None,
    ):
        if isinstance(entity, dict):
            return entity
        if isinstance(entity, BaseModel):
            if fields:
                fields = set(fields)
                if len(fields) == 1:
                    if flat:
                        return entity.dict(
                            include=fields, by_alias=by_alias, exclude=exclude
                        )[next(iter(fields))]
                    return entity.dict(
                        include=fields, by_alias=by_alias, exclude=exclude
                    )
                return entity.dict(include=fields, by_alias=by_alias, exclude=exclude)
            return entity.dict(by_alias=by_alias, exclude=exclude)
        return entity.to_dict()

    @classmethod
    def serialize_iterable(
        cls,
        data: List[Any],
        fields: Union[List[str], Set[str]] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set = None,
    ) -> List[Any]:
        serialized_data = []
        for i in data:
            serialized_data.append(
                cls._fill_enum_values(
                    cls._serialize(i, fields, by_alias, flat, exclude=exclude)
                )
            )
        return serialized_data


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
    DEFAULT_EXCLUDE_SET = {"sync_status", "unverified_users"}

    def serialize(
        self,
        fields: List[str] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set[str] = None,
    ):
        to_exclude = self.DEFAULT_EXCLUDE_SET
        if exclude:
            to_exclude = exclude.union(self.DEFAULT_EXCLUDE_SET)
        data = super().serialize(fields, by_alias, flat, to_exclude)
        if data.get("settings"):
            data["settings"] = [
                SettingsSerializer(setting).serialize() for setting in data["settings"]
            ]
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


class SettingsSerializer(BaseSerializer):
    def serialize(
        self,
        fields: List[str] = None,
        by_alias: bool = True,
        flat: bool = False,
        exclude=None,
    ):
        data = super().serialize(fields, by_alias, flat, exclude)
        if data["attribute"] == "ImageQuality":
            data["value"] = constance.ImageQuality.get_name(data["value"])
        return data
