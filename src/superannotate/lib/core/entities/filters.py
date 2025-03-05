from typing import List
from typing import Literal
from typing import Optional

from typing_extensions import TypedDict


class BaseFilters(TypedDict, total=False):
    id: Optional[int]
    id__in: Optional[List[int]]
    name: Optional[str]
    name__in: Optional[List[str]]
    name__contains: Optional[str]
    name__starts: Optional[str]
    name__ends: Optional[str]


class ItemFilters(BaseFilters):
    annotation_status: Optional[str]
    annotation_status__in: Optional[List[str]]
    annotation_status__ne: Optional[List[str]]
    approval_status: Optional[str]
    approval_status__in: Optional[List[str]]
    approval_status__ne: Optional[str]
    assignments__user_id: Optional[str]
    assignments__user_id__in: Optional[List[str]]
    assignments__user_id__ne: Optional[str]
    assignments__user_role: Optional[str]
    assignments__user_role__in: Optional[List[str]]
    assignments__user_role__ne: Optional[str]
    assignments__user_role__notin: Optional[List[str]]
    categories__value: Optional[str]
    categories__value__in: Optional[List[str]]


class ProjectFilters(BaseFilters):
    status: Literal["NotStarted", "InProgress", "Completed", "OnHold"]
    status__ne: Literal["NotStarted", "InProgress", "Completed", "OnHold"]
    status__in: List[Literal["NotStarted", "InProgress", "Completed", "OnHold"]]
    status__notin: List[Literal["NotStarted", "InProgress", "Completed", "OnHold"]]


class UserFilters(TypedDict, total=False):
    id: Optional[int]
    id__in: Optional[List[int]]
    email: Optional[str]
    email__in: Optional[List[str]]
    email__contains: Optional[str]
    email__starts: Optional[str]
    email__ends: Optional[str]
    state: Optional[str]
    state__in: Optional[List[str]]
    role: Optional[str]
    role__in: Optional[List[str]]
