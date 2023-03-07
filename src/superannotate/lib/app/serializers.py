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
        exclude_unset=False,
    ):
        return self._fill_enum_values(
            self._serialize(
                self._entity,
                fields,
                by_alias,
                flat,
                exclude=exclude,
                exclude_unset=exclude_unset,
            )
        )

    @staticmethod
    def _serialize(
        entity: Any,
        fields: List[str] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set[str] = None,
        **kwargs
    ):
        if not entity:
            return None
        if isinstance(entity, dict):
            return entity
        if isinstance(entity, BaseModel):
            if fields:
                fields = set(fields)
                if len(fields) == 1:
                    if flat:
                        return entity.dict(
                            include=fields, by_alias=by_alias, exclude=exclude, **kwargs
                        )[next(iter(fields))]
                    return entity.dict(
                        include=fields, by_alias=by_alias, exclude=exclude, **kwargs
                    )
                return entity.dict(
                    include=fields, by_alias=by_alias, exclude=exclude, **kwargs
                )
            return entity.dict(by_alias=by_alias, exclude=exclude, **kwargs)
        return entity.to_dict()

    @classmethod
    def serialize_iterable(
        cls,
        data: List[Any],
        fields: Union[List[str], Set[str]] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set = None,
        **kwargs
    ) -> List[Any]:
        serialized_data = []
        for i in data:
            serialized_data.append(
                cls._fill_enum_values(
                    cls._serialize(i, fields, by_alias, flat, exclude=exclude, **kwargs)
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
    def serialize(
        self,
        fields: List[str] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set[str] = None,
    ):

        to_exclude = {
            "sync_status": True,
            "unverified_users": True,
            "classes": {
                "__all__": {"attribute_groups": {"__all__": {"is_multiselect"}}}
            },
        }
        if exclude:
            for field in exclude:
                to_exclude[field] = True

        data = super().serialize(fields, by_alias, flat, to_exclude)
        if data.get("settings"):
            data["settings"] = [
                SettingsSerializer(setting).serialize() for setting in data["settings"]
            ]

        if not data.get("status"):
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
    def serialize(
        self,
        fields: List[str] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set[str] = None,
    ):
        data = super().serialize(fields, by_alias, flat, exclude)
        if not data.get("status"):
            data["status"] = "Undefined"

        return data


class SettingsSerializer:
    def __init__(self, data: dict):
        self.data = data

    def serialize(self):
        if self.data["attribute"] == "ImageQuality":
            self.data["value"] = constance.ImageQuality.get_name(self.data["value"])
        return self.data


class ItemSerializer(BaseSerializer):
    def serialize(
        self,
        fields: List[str] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set[str] = None,
    ):
        data = super().serialize(fields, by_alias, flat, exclude)

        return data


class EntitySerializer:
    @classmethod
    def serialize(
        cls, data: Union[BaseModel, List[BaseModel]], **kwargs
    ) -> Union[List[dict], dict]:
        if isinstance(data, (list, set)):
            for idx, item in enumerate(data):
                data[idx] = cls.serialize(item, **kwargs)
        for key, nested_model in data:
            if isinstance(nested_model, BaseModel) and getattr(
                nested_model, "fill_enum_values", False
            ):
                setattr(data, key, cls.serialize(nested_model, **kwargs))
        return data.dict(**kwargs)
