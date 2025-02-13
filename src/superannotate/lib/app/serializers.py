from abc import ABC
from enum import Enum
from typing import Any
from typing import List
from typing import Set
from typing import Union

import lib.core as constance
from lib.core.entities import BaseEntity
from lib.core.pydantic_v1 import BaseModel


class BaseSerializer(ABC):
    def __init__(self, entity: BaseEntity):
        self._entity = entity

    @staticmethod
    def _fill_enum_values(data: dict):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, Enum):
                    data[key] = value.name
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
            fields = set(fields) if fields else None
            if fields:
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
        **kwargs: object
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
    ...


class ProjectSerializer(BaseSerializer):
    def serialize(
        self,
        fields: List[str] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set[str] = None,
        exclude_unset=False,
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
        if self._entity.classes:
            self._entity.classes = [
                i.dict(by_alias=True, exclude_unset=True) for i in self._entity.classes
            ]
        data = super().serialize(fields, by_alias, flat, to_exclude)
        if data.get("settings"):
            data["settings"] = [
                SettingsSerializer(setting).serialize() for setting in data["settings"]
            ]

        if not data.get("status"):
            data["status"] = "Undefined"

        if data.get("upload_state"):
            data["upload_state"] = constance.UploadState(data["upload_state"]).name
        return data


class WMProjectSerializer(BaseSerializer):
    def serialize(
        self,
        fields: List[str] = None,
        by_alias: bool = False,
        flat: bool = False,
        exclude: Set[str] = None,
        exclude_unset=False,
    ):

        to_exclude = {"sync_status": True, "unverified_users": True, "classes": True}
        if exclude:
            for field in exclude:
                to_exclude[field] = True
        data = super().serialize(fields, by_alias, flat, to_exclude)
        if not data.get("status"):
            data["status"] = "Undefined"
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
            self.data["value"] = constance.ImageQuality(self.data["value"]).name
        return self.data


class ItemSerializer(BaseSerializer):
    ...


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
