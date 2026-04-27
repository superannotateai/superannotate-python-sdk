from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict


class BaseFilters(TypedDict, total=False):
    id: int | None
    id__in: list[int] | None
    name: str | None
    name__in: list[str] | None
    name__contains: str | None
    name__starts: str | None
    name__ends: str | None


class ItemFilters(BaseFilters):
    annotation_status: str | None
    annotation_status__in: list[str] | None
    annotation_status__ne: str | None
    annotation_status__notin: list[str] | None
    approval_status: str | None
    approval_status__in: list[str] | None
    approval_status__ne: str | None
    assignments__user_id: str | None
    assignments__user_id__in: list[str] | None
    assignments__user_id__ne: str | None
    assignments__user_role: str | None
    assignments__user_role__in: list[str] | None
    assignments__user_role__ne: str | None
    assignments__user_role__notin: list[str] | None
    categories__value: str | None
    categories__value__in: list[str] | None


class ProjectFilters(BaseFilters):
    status: Literal["NotStarted", "InProgress", "Completed", "OnHold"]
    status__ne: Literal["NotStarted", "InProgress", "Completed", "OnHold"]
    status__in: list[Literal["NotStarted", "InProgress", "Completed", "OnHold"]]
    status__notin: list[Literal["NotStarted", "InProgress", "Completed", "OnHold"]]


class FolderFilters(ProjectFilters):
    pass


class BaseUserFilters(TypedDict, total=False):
    id: int | None
    id__in: list[int] | None
    email: str | None
    email__in: list[str] | None
    email__contains: str | None
    email__starts: str | None
    email__ends: str | None


class ProjectUserFilters(BaseUserFilters, total=False):
    role: str | None
    role__in: list[str] | None


class TeamUserFilters(BaseUserFilters, total=False):
    state: str | None
    state__in: list[str] | None
    role: str | None
    role__in: list[str] | None
