import collections
import copy
import io
import json
import logging
import os
import sys
import typing
import warnings
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from typing_extensions import Literal

if sys.version_info < (3, 11):
    from typing_extensions import TypedDict, NotRequired, Required  # noqa
else:
    from typing import TypedDict, NotRequired, Required  # noqa

import boto3

from tqdm import tqdm

import lib.core as constants
from lib.infrastructure.controller import Controller
from lib.app.helpers import get_annotation_paths
from lib.app.helpers import get_name_url_duplicated_from_csv
from lib.app.helpers import wrap_error as wrap_validation_errors
from lib.app.interface.base_interface import BaseInterfaceFacade
from lib.app.interface.base_interface import TrackableMeta

from lib.app.interface.types import EmailStr
from lib.app.serializers import BaseSerializer
from lib.app.serializers import FolderSerializer
from lib.app.serializers import ProjectSerializer
from lib.app.serializers import SettingsSerializer
from lib.app.serializers import TeamSerializer
from lib.core import LIMITED_FUNCTIONS
from lib.core import entities
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.conditions import Condition
from lib.core.jsx_conditions import Filter, OperatorEnum
from lib.core.conditions import EmptyCondition
from lib.core.entities import AttachmentEntity, FolderEntity, BaseItemEntity
from lib.core.entities import SettingEntity
from lib.core.entities.classes import AnnotationClassEntity
from lib.core.entities.classes import AttributeGroup
from lib.core.entities.integrations import IntegrationEntity
from lib.core.entities.integrations import IntegrationTypeEnum
from lib.core.enums import ImageQuality
from lib.core.enums import CustomFieldEntityEnum
from lib.core.enums import ProjectType
from lib.core.enums import ClassTypeEnum
from lib.core.exceptions import AppException
from lib.core.types import PriorityScoreEntity
from lib.core.types import Project
from lib.core.pydantic_v1 import ValidationError
from lib.core.pydantic_v1 import constr
from lib.core.pydantic_v1 import conlist
from lib.core.pydantic_v1 import parse_obj_as
from lib.infrastructure.annotation_adapter import BaseMultimodalAnnotationAdapter
from lib.infrastructure.annotation_adapter import MultimodalSmallAnnotationAdapter
from lib.infrastructure.annotation_adapter import MultimodalLargeAnnotationAdapter
from lib.infrastructure.utils import extract_project_folder
from lib.infrastructure.validators import wrap_error
from lib.app.serializers import WMProjectSerializer
from lib.core.entities.work_managament import WMUserTypeEnum
from lib.core.jsx_conditions import EmptyQuery

logger = logging.getLogger("sa")

NotEmptyStr = constr(strict=True, min_length=1)

PROJECT_STATUS = Literal["NotStarted", "InProgress", "Completed", "OnHold"]

PROJECT_TYPE = Literal[
    "Vector",
    "Pixel",
    "Video",
    "Document",
    "Tiled",
    "PointCloud",
    "Multimodal",
]

APPROVAL_STATUS = Literal["Approved", "Disapproved", None]

IMAGE_QUALITY = Literal["compressed", "original"]

ANNOTATION_TYPE = Literal["bbox", "polygon", "point", "tag"]

ANNOTATOR_ROLE = Literal["Admin", "Annotator", "QA"]

FOLDER_STATUS = Literal["NotStarted", "InProgress", "Completed", "OnHold"]


class Setting(TypedDict):
    attribute: str
    value: Union[str, float, int]


class PriorityScore(TypedDict):
    name: str
    priority: float


class Attachment(TypedDict, total=False):
    url: Required[str]  # noqa
    name: NotRequired[str]  # noqa
    integration: NotRequired[str]  # noqa


class ItemContext:
    """
    A context manager for handling annotations and metadata of an item.

    The ItemContext class provides methods to retrieve and manage metadata and component
    values for items in the specified context. Below are the descriptions and usage examples for each method.

    Example:
    ::

        with sa_client.item_context("project_name/folder_name", "item_name") as context:
            metadata = context.get_metadata()
            print(metadata)
    """

    def __init__(
        self,
        controller: Controller,
        project: Project,
        folder: FolderEntity,
        item: BaseItemEntity,
        overwrite: bool = True,
    ):
        self.controller = controller
        self.project = project
        self.folder = folder
        self.item = item
        self._annotation_adapter: Optional[BaseMultimodalAnnotationAdapter] = None
        self._overwrite = overwrite
        self._annotation = None

    def _set_small_annotation_adapter(self, annotation: dict = None):
        self._annotation_adapter = MultimodalSmallAnnotationAdapter(
            project=self.project,
            folder=self.folder,
            item=self.item,
            controller=self.controller,
            overwrite=self._overwrite,
            annotation=annotation,
        )

    def _set_large_annotation_adapter(self, annotation: dict = None):
        self._annotation_adapter = MultimodalLargeAnnotationAdapter(
            project=self.project,
            folder=self.folder,
            item=self.item,
            controller=self.controller,
            annotation=annotation,
        )

    @property
    def annotation_adapter(self) -> BaseMultimodalAnnotationAdapter:
        if self._annotation_adapter is None:
            res = self.controller.service_provider.annotations.get_upload_chunks(
                project=self.project, item_ids=[self.item.id]
            )
            small_item = next(iter(res["small"]), None)
            if small_item:
                self._set_small_annotation_adapter()
            else:
                self._set_large_annotation_adapter()
        return self._annotation_adapter

    @property
    def annotation(self):
        return self.annotation_adapter.annotation

    def __enter__(self):
        """
        Enters the context manager.

        Returns:
        ItemContext: The instance itself.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exits the context manager, saving changes if no exception occurred.

        Args:
            exc_type (Optional[Type[BaseException]]): Exception type if raised.
            exc_val (Optional[BaseException]): Exception instance if raised.
            exc_tb (Optional[TracebackType]): Traceback if an exception occurred.

        Returns:
            bool: True if no exception occurred, False otherwise.
        """
        if exc_type:
            return False

        self.save()
        return True

    def save(self):
        if len(json.dumps(self.annotation).encode("utf-8")) > 15 * 1024 * 1024:
            self._set_large_annotation_adapter(self.annotation)
        else:
            self._set_small_annotation_adapter(self.annotation)
        self._annotation_adapter.save()

    def get_metadata(self):
        """
        Retrieves the metadata associated with the current item context.

        :return: A dictionary containing metadata for the current item.
        :rtype: dict

        Request Example:
        ::

            with client.item_context(("project_name", "folder_name"), 12345) as context:
                metadata = context.get_metadata()
                print(metadata)
        """
        return self.annotation["metadata"]

    def get_component_value(self, component_id: str):
        """
        Retrieves the value of a specific component within the item context.

        :param component_id: The name of the component whose value is to be retrieved.
        :type component_id: str

        :return: The value of the specified component.
        :rtype: Any

        Request Example:
        ::

            with client.item_context((101, 202), "item_name") as context: # (101, 202) project and folder IDs
                value = context.get_component_value("component_id")
                print(value)
        """
        return self.annotation_adapter.get_component_value(component_id)

    def set_component_value(self, component_id: str, value: Any):
        """
        Updates the value of a specific component within the item context.

        :param component_id: The component identifier.
        :type component_id: str

        :param value: The new value to set for the specified component.
        :type value: Any

        :return: The instance itself to allow method chaining.
        :rtype: ItemContext

        Request Example:
        ::

            with client.item_context("project_name/folder_name", "item_name") as item_context:
                metadata = item_context.get_metadata()
                value = item_context.get_component_value("component_id")
                item_context.set_component_value("component_id", value)

        """
        self.annotation_adapter.set_component_value(component_id, value)
        return self


class SAClient(BaseInterfaceFacade, metaclass=TrackableMeta):
    """Create SAClient instance to authorize SDK in a team scope.
    In case of no argument has been provided, SA_TOKEN environmental variable
    will be checked or $HOME/.superannotate/config.json will be used.

    :param token: team token
    :type token: str

    :param config_path: path to config file
    :type config_path: path-like (str or Path)

    """

    def __init__(
        self,
        token: str = None,
        config_path: str = None,
    ):
        super().__init__(token, config_path)

    def get_project_by_id(self, project_id: int):
        """Returns the project metadata

        :param project_id: the id of the project
        :type project_id: int

        :return: project metadata
        :rtype: dict
        """
        response = self.controller.get_project_by_id(project_id=project_id)

        return ProjectSerializer(response.data).serialize()

    def get_folder_by_id(self, project_id: int, folder_id: int):
        """Returns the folder metadata

        :param project_id: the id of the project
        :type project_id: int

        :param folder_id: the id of the folder
        :type folder_id: int

        :return: folder metadata
        :rtype: dict
        """

        response = self.controller.get_folder_by_id(
            folder_id=folder_id, project_id=project_id
        )
        response.raise_for_status()
        return FolderSerializer(response.data).serialize(
            exclude={"completedCount", "is_root"}
        )

    def get_item_by_id(self, project_id: int, item_id: int):
        """Returns the item metadata

        :param project_id: the id of the project
        :type project_id: int

        :param item_id: the id of the item
        :type item_id: int

        :return: item metadata
        :rtype: dict
        """
        project_response = self.controller.get_project_by_id(project_id=project_id)
        project_response.raise_for_status()
        item = self.controller.get_item_by_id(
            item_id=item_id, project=project_response.data
        )

        return BaseSerializer(item).serialize(exclude={"url", "meta"})

    def get_team_metadata(self, include: List[Literal["scores"]] = None):
        """
        Returns team metadata, including optionally, scores.

        :param include: Specifies additional fields to include in the response.

            Possible values are

            - "scores": If provided, the response will include score names associated with the team user.

        :type include: list of str, optional

        :return: team metadata
        :rtype: dict
        """
        response = self.controller.get_team()
        team = response.data
        if include and "scores" in include:
            team.scores = [
                i.name
                for i in self.controller.work_management.list_score_templates().data
            ]
        return TeamSerializer(team).serialize(exclude_unset=True)

    def get_user_metadata(
        self, pk: Union[int, str], include: List[Literal["custom_fields"]] = None
    ):
        """
        Returns user metadata including optionally, custom fields

        :param pk: The email address or ID of the team user.
        :type pk: str or int

        :param include: Specifies additional fields to include in the response.

            Possible values are

            - "custom_fields": If provided, the response will include custom fields associated with the team user.

        :type include: list of str, optional

        :return: metadata of team user.
        :rtype: dict

        Request Example:
        ::

            client.get_user_metadata(
                "example@email.com",
                include=["custom_fields"]
            )

        Response Example:
        ::

            {
                "createdAt": "2023-11-27T07:10:24.000Z",
                "updatedAt": "2025-02-03T13:35:09.000Z",
                "custom_fields": {
                    "ann_quality_threshold": 80,
                    "tag": ["Tag1", "Tag2", "Tag3"],
                    "due_date": 1738671238.7,
                },
                "email": "example@email.com",
                "id": 124341,
                "role": "Contributor",
                "state": "Confirmed",
                "team_id": 23245,
            }
        """
        user = self.controller.work_management.get_user_metadata(pk=pk, include=include)
        return BaseSerializer(user).serialize(by_alias=False)

    def set_user_custom_field(
        self, pk: Union[int, str], custom_field_name: str, value: Any
    ):
        """
        Set the custom field for team user.

        :param pk: The email address or ID of the team user.
        :type pk: str or int

        :param custom_field_name: The name of the existing custom field assigned to the user.
        :type custom_field_name: str

        :param value: The new value for the custom field.

            - This can be a string, a list of strings, a number, or None depending on the custom field type.
            - Multi-select fields must be provided as a list of strings (e.g., ["Tag1", "Tag2"]).
            - Date fields must be in Unix timestamp format (e.g., "1738281600").
            - Other fields (e.g., text, numbers) should match the expected type as defined in the project schema.
        :type value: Any

        Request Example:
        ::

            client.set_user_custom_field(
                "example@email.com",
                custom_field_name="due_date",
                value=1738671238.7
            )
        """
        user = self.controller.work_management.get_user_metadata(pk=pk)
        if user.role == WMUserTypeEnum.TeamOwner:
            raise AppException(
                "Setting custom fields for the Team Owner is not allowed."
            )
        self.controller.work_management.set_custom_field_value(
            entity_id=user.id,
            field_name=custom_field_name,
            value=value,
            entity=CustomFieldEntityEnum.CONTRIBUTOR,
            parent_entity=CustomFieldEntityEnum.TEAM,
        )

    def list_users(
        self,
        *,
        project: Union[int, str] = None,
        include: List[Literal["custom_fields"]] = None,
        **filters,
    ):
        """
        Search users, including their scores, by filtering criteria.

        :param project:  Project name or ID, if provided, results will be for project-level,
         otherwise results will be for team level.
        :type project: str or int

        :param include: Specifies additional fields to be included in the response.

            Possible values are

            - "custom_fields":  Includes custom fields and scores assigned to each user.

        :param filters: Specifies filtering criteria, with all conditions combined using logical AND.

            - Only users matching all filter conditions are returned.

            - If no filter operation is provided, an exact match is applied

            Supported operations:

            - __in: Value is in the provided list.
            - __notin: Value is not in the provided list.
            - __ne: Value is not equal to the given value.
            - __contains: Value contains the specified substring.
            - __starts: Value starts with the given prefix.
            - __ends: Value ends with the given suffix.
            - __gt: Value is greater than the given number.
            - __gte: Value is greater than or equal to the given number.
            - __lt: Value is less than the given number.
            - __lte: Value is less than or equal to the given number.

            Filter params::

            - id: int
            - id__in: list[int]
            - email: str
            - email__in:  list[str]
            - email__contains: str
            - email__starts: str
            - email__ends: str

            Following params if project is not selected::

            - state: Literal[“Confirmed”, “Pending”]
            - state__in: List[Literal[“Confirmed”, “Pending”]]
            - role: Literal[“admin”, “contributor”]
            - role__in: List[Literal[“admin”, “contributor”]]

            Scores and Custom Field Filtering:

                - Scores and other custom fields must be prefixed with `custom_field__` .
                - Example: custom_field__Due_date__gte="1738281600" (filtering users whose Due_date is after the given Unix timestamp).

            - **Text** custom field only works with the following filter params: __in, __notin, __contains
            - **Numeric** custom field only works with the following filter params: __in, __notin, __ne, __gt, __gte, __lt, __lte
            - **Single-select** custom field only works with the following filter params: __in, __notin, __contains
            - **Multi-select** custom field only works with the following filter params: __in, __notin
            - **Date picker** custom field only works with the following filter params: __gt, __gte, __lt, __lte

            **If custom field has a space, please use the following format to filter them**:
            ::

                user_filters = {"custom_field__accuracy score 30D__lt": 90}
                client.list_users(include=["custom_fields"], **user_filters)


        :type filters: UserFilters, optional

        :return: A list of team/project users metadata that matches the filtering criteria
        :rtype: list of dicts

        Request Example:
        ::

            client.list_users(
                email__contains="@superannotate.com",
                include=["custom_fields"],
                state__in=["Confirmed"]
                custom_fields__Tag__in=["Tag1", "Tag3"]
            )

        Response Example:
        ::

            [
                {
                    "createdAt": "2023-02-02T14:25:42.000Z",
                    "updatedAt": "2025-01-23T16:39:03.000Z",
                    "custom_fields": {
                        "Ann Quality threshold": 80,
                        "Tag": ["Tag1", "Tag2", "Tag3"],
                    },
                    "email": "example@superannotate.com",
                    "id": 30328,
                    "role": "TeamOwner",
                    "state": "Confirmed",
                    "team_id": 44311,
                }
            ]

        Request Example:
        ::

            # Project level scores

            scores = client.list_users(
                include=["custom_fields"],
                project="my_multimodal",
                email__contains="@superannotate.com",
                custom_field__speed__gte=90,
                custom_field__weight__lte=1,
            )

        Response Example:
        ::

            # Project level scores

            [
                {
                    "createdAt": "2025-03-07T13:19:59.000Z",
                    "updatedAt": "2025-03-07T13:19:59.000Z",
                    "custom_fields": {"speed": 92, "weight": 0.8},
                    "email": "example@superannotate.com",
                    "id": 715121,
                    "role": "Annotator",
                    "state": "Confirmed",
                    "team_id": 1234,
                }
            ]

        Request Example:
        ::

            # Team level scores

            user_filters = {
                "custom_field__accuracy score 30D__lt": 95,
                "custom_field__speed score 7D__lt": 15
            }

            scores = client.list_users(
                include=["custom_fields"],
                email__contains="@superannotate.com",
                role="Contributor",
                **user_filters
            )

        Response Example:
        ::

            # Team level scores

            [
                {
                    "createdAt": "2025-03-07T13:19:59.000Z",
                    "updatedAt": "2025-03-07T13:19:59.000Z",
                    "custom_fields": {
                        "Test custom field": 80,
                        "Tag custom fields": ["Tag1", "Tag2"],
                        "accuracy score 30D": 95,
                        "accuracy score 14D": 47,
                        "accuracy score 7D": 24,
                        "speed score 30D": 33,
                        "speed score 14D": 22,
                        "speed score 7D": 11,
                    },
                    "email": "example@superannotate.com",
                    "id": 715121,
                    "role": "Contributor",
                    "state": "Confirmed",
                    "team_id": 1234,
                }
            ]

        """
        if project is not None:
            if isinstance(project, int):
                project = self.controller.get_project_by_id(project)
            else:
                project = self.controller.get_project(project)
        response = BaseSerializer.serialize_iterable(
            self.controller.work_management.list_users(
                project=project, include=include, **filters
            )
        )
        if project:
            for user in response:
                user["role"] = self.controller.service_provider.get_role_name(
                    project, user["role"]
                )
        return response

    def pause_user_activity(
        self, pk: Union[int, str], projects: Union[List[int], List[str], Literal["*"]]
    ):
        """
        Block the team contributor from requesting items from the projects.

        :param pk: The email address or user ID of the team contributor.
        :type pk: str or int

        :param projects: A list of project names or IDs from which the user should be blocked.
                        The special value "*" means block access to all projects
        :type projects: Union[List[int], List[str], Literal["*"]]
        """
        user = self.controller.work_management.get_user_metadata(pk=pk)
        if user.role is not WMUserTypeEnum.Contributor:
            raise AppException("User must have a contributor role to pause activity.")
        self.controller.work_management.update_user_activity(
            user_email=user.email, provided_projects=projects, action="pause"
        )
        logger.info(
            f"User with email {user.email} has been successfully paused from the specified projects: {projects}."
        )

    def resume_user_activity(
        self, pk: Union[int, str], projects: Union[List[int], List[str], Literal["*"]]
    ):
        """
        Resume the team contributor from requesting items from the projects.

        :param pk: The email address or user ID of the team contributor.
        :type pk: str or int

        :param projects: A list of project names or IDs from which the user should be resumed.
                        The special value "*" means resume access to all projects
        :type projects: Union[List[int], List[str], Literal["*"]]
        """
        user = self.controller.work_management.get_user_metadata(pk=pk)
        if user.role is not WMUserTypeEnum.Contributor:
            raise AppException("User must have a contributor role to resume activity.")
        self.controller.work_management.update_user_activity(
            user_email=user.email, provided_projects=projects, action="resume"
        )
        logger.info(
            f"User with email {user.email} has been successfully unblocked from the specified projects: {projects}."
        )

    def get_user_scores(
        self,
        project: Union[NotEmptyStr, Tuple[int, int], Tuple[str, str]],
        item: Union[NotEmptyStr, int],
        scored_user: NotEmptyStr,
        *,
        score_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve score metadata for a user for a specific item in a specific project.

        :param project: Project and folder as a tuple, folder is optional.
        :type project: Union[str, Tuple[int, int], Tuple[str, str]]

        :param item:  The unique ID or name of the item.
        :type item: Union[str, int]

        :param scored_user:  The email address of the project user.
        :type scored_user: str

        :param score_names:  A list of score names to filter by. If None, returns all scores.
        :type score_names: Optional[List[str]]

        :return: A list of dictionaries containing score metadata for the user.
        :rtype: list of dicts

        Request Example:
        ::

            client.get_user_scores(
                project=("my_multimodal", "folder1"),
                item="item1",
                scored_user="example@superannotate.com",
                score_names=["Accuracy Score", "Speed"]
            )

        Response Example:
        ::

            [
                {
                    "createdAt": "2024-06-01T13:00:00",
                    "updatedAt": "2024-06-01T13:00:00",
                    "id": 3217575,
                    "name": "Accuracy Score",
                    "value": 98,
                    "weight": 4,
                },
                {
                    "createdAt": "2024-06-01T13:00:00",
                    "updatedAt": "2024-06-01T13:00:00",
                    "id": 5657575,
                    "name": "Speed",
                    "value": 9,
                    "weight": 0.4,
                },
            ]
        """
        project, folder = self.controller.get_project_folder(project)
        if project.type != ProjectType.MULTIMODAL:
            raise AppException(
                "This function is only supported for Multimodal projects."
            )

        item = self.controller.get_item(project=project, folder=folder, item=item)
        response = BaseSerializer.serialize_iterable(
            self.controller.work_management.get_user_scores(
                project=project,
                item=item,
                scored_user=scored_user,
                provided_score_names=score_names,
            )
        )
        return response

    def set_user_scores(
        self,
        project: Union[NotEmptyStr, Tuple[int, int], Tuple[str, str]],
        item: Union[NotEmptyStr, int],
        scored_user: NotEmptyStr,
        scores: List[Dict[str, Any]],
    ):
        """
        Assign score metadata for a user in a scoring component.

        :param project: Project and folder as a tuple, folder is optional.
        :type project: Union[str, Tuple[int, int], Tuple[str, str]]

        :param item:  The unique ID or name of the item.
        :type item: Union[str, int]

        :param scored_user:  Set the email of the user being scored.
        :type scored_user: str

        :param scores: A list of dictionaries containing the following key-value pairs:
                * **component_id** (*str*): The component_id of the score (required).
                * **value** (*Any*): The score value (required).
                * **weight** (*Union[float, int]*, optional): The weight of the score. Defaults to `1` if not provided.

            **Example**:
            ::

                scores = [
                    {
                        "component_id": "<component_id_for_score>",  # str (required)
                        "value": 90,      # Any (required)
                        "weight": 1       # Union[float, int] (optional, defaults to 1.0 if not provided)
                    }
                ]
        :type scores: List[Dict[str, Any]

        Request Example:
        ::

            client.set_user_scores(
                project=("my_multimodal", "folder1"),
                item_=12345,
                scored_user="example@superannotate.com",
                scores=[
                    {"component_id": "r_kfrp3n", "value": 90},
                    {"component_id": "h_jbrp4v", "value": 9, "weight": 4.0},
                    {"component_id": "m_kf8pss", "value": None, "weight": None},
                ]
            )

        """
        project, folder = self.controller.get_project_folder(project)
        if project.type != ProjectType.MULTIMODAL:
            raise AppException(
                "This function is only supported for Multimodal projects."
            )
        item = self.controller.get_item(project=project, folder=folder, item=item)
        editor_template = self.controller.projects.get_editor_template(project.id)
        components = editor_template.get("components", [])
        self.controller.work_management.set_user_scores(
            project=project,
            item=item,
            scored_user=scored_user,
            scores=scores,
            components=components,
        )
        logger.info("Scores successfully set.")

    def get_component_config(self, project: Union[NotEmptyStr, int], component_id: str):
        """
        Retrieves the configuration for a given project and component ID.

        :param project: The identifier of the project, which can be a string or an integer representing the project ID.
        :type project: Union[str, int]

        :param component_id: The ID of the component for which the context is to be retrieved.
        :type component_id: str

        :return: The context associated with the `webComponent`.
        :rtype: Any

        :raises AppException: If the project type is not `MULTIMODAL` or no `webComponent` context is found.
        """

        def retrieve_context(
            component_data: List[dict], component_pk: str
        ) -> Tuple[bool, typing.Any]:
            try:
                for component in component_data:
                    if "children" in component:
                        found, val = retrieve_context(
                            component["children"], component_pk
                        )
                        if found:
                            return found, val
                    if (
                        "id" in component
                        and component["id"] == component_pk
                        and component["type"] == "webComponent"
                    ):
                        context = component.get("context")
                        if context is None or context == "":
                            return False, None
                        return True, json.loads(component.get("context"))

            except KeyError as e:
                logger.debug("Got key error:", component_data)
                raise e
            return False, None

        project = (
            self.controller.get_project_by_id(project).data
            if isinstance(project, int)
            else self.controller.get_project(project)
        )
        if project.type != ProjectType.MULTIMODAL:
            raise AppException(
                "This function is only supported for Multimodal projects."
            )

        editor_template = self.controller.projects.get_editor_template(project.id)
        components = editor_template.get("components", [])

        _found, _context = retrieve_context(components, component_id)
        if not _found:
            raise AppException("No component context found for project.")
        return _context

    def search_team_contributors(
        self,
        email: EmailStr = None,
        first_name: NotEmptyStr = None,
        last_name: NotEmptyStr = None,
        return_metadata: bool = True,
    ):
        """Search for contributors in the team

        :param email: filter by email
        :type email: str

        :param first_name: filter by first name
        :type first_name: str

        :param last_name: filter by last name
        :type last_name: str

        :param return_metadata: return metadata of contributors instead of names
        :type return_metadata: bool

        :return: metadata of found users
        :rtype: list of dicts
        """

        contributors = self.controller.search_team_contributors(
            email=email, first_name=first_name, last_name=last_name
        ).data

        if not return_metadata:
            return [contributor["email"] for contributor in contributors]
        return contributors

    def search_projects(
        self,
        name: Optional[NotEmptyStr] = None,
        return_metadata: bool = False,
        include_complete_item_count: bool = False,
        status: Optional[Union[PROJECT_STATUS, List[PROJECT_STATUS]]] = None,
    ):
        """
        Project name based case-insensitive search for projects.
        If **name** is None, all the projects will be returned.

        :param name: search string
        :type name: str

        :param return_metadata: return metadata of projects instead of names
        :type return_metadata: bool

        :param include_complete_item_count: return projects that have completed items and include
            the number of completed items in response.
        :type include_complete_item_count: bool

        :param status: search projects via project status
        :type status: str

        :return: project names or metadatas
        :rtype: list of strs or dicts
        """
        statuses = []
        if status:
            if isinstance(status, (list, tuple, set)):
                statuses = list(status)
            else:
                statuses = [status]

        condition = Condition.get_empty_condition()
        if name:
            condition &= Condition("name", name, EQ)
        if include_complete_item_count:
            condition &= Condition(
                "completeImagesCount", include_complete_item_count, EQ
            )
        for _status in statuses:
            condition &= Condition("status", constants.ProjectStatus(_status).value, EQ)

        response = self.controller.projects.list(condition)
        if response.errors:
            raise AppException(response.errors)
        if return_metadata:
            return [
                ProjectSerializer(project).serialize(
                    exclude={
                        "settings",
                        "workflows",
                        "contributors",
                        "classes",
                        "item_count",
                    }
                )
                for project in response.data
            ]
        return [project.name for project in response.data]

    def create_project(
        self,
        project_name: NotEmptyStr,
        project_description: NotEmptyStr,
        project_type: PROJECT_TYPE,
        settings: List[Setting] = None,
        classes: List[AnnotationClassEntity] = None,
        workflows: Any = None,
        instructions_link: str = None,
        workflow: str = None,
    ):
        """Create a new project in the team.

        :param project_name: the new project's name
        :type project_name: str

        :param project_description: the new project's description
        :type project_description: str

        :param project_type: the new project type, Vector, Pixel, Video, Document, Tiled, PointCloud, Multimodal.
        :type project_type: str

        :param settings: list of settings objects
        :type settings: list of dicts

        :param classes: list of class objects
        :type classes: list of dicts

        :param workflows: Deprecated
        :type workflows: list of dicts

        :param workflow: the name of the workflow already created within the team, which must match exactly.
                         If None, the default “System workflow” workflow will be set.
        :type workflow: str

        :param instructions_link: str of instructions URL
        :type instructions_link: str

        :return: dict object metadata the new project
        :rtype: dict
        """
        if workflows is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “workflows” parameter is deprecated. Please use the “set_project_steps” function instead."
                )
            )
        if settings:
            settings = parse_obj_as(List[SettingEntity], settings)
        else:
            settings = []
        if classes:
            classes = parse_obj_as(List[AnnotationClassEntity], classes)
        project_entity = entities.ProjectEntity(
            name=project_name,
            description=project_description,
            type=constants.ProjectType(project_type).value,
            settings=settings,
            instructions_link=instructions_link,
        )
        if workflow:
            _workflows = (
                self.controller.service_provider.work_management.list_workflows(
                    Filter("name", workflow, OperatorEnum.EQ)
                )
            )
            _workflow = next((i for i in _workflows.data if i.name == workflow), None)
            if not _workflow:
                raise AppException("Workflow not fund.")
            project_entity.workflow_id = _workflow.id
        project_response = self.controller.projects.create(project_entity)
        project_response.raise_for_status()
        project = project_response.data
        if classes:
            classes_response = self.controller.annotation_classes.create_multiple(
                project, classes
            )
            classes_response.raise_for_status()
            project.classes = classes_response.data
        return ProjectSerializer(project).serialize()

    def clone_project(
        self,
        project_name: Union[NotEmptyStr, dict],
        from_project: Union[NotEmptyStr, dict],
        project_description: Optional[NotEmptyStr] = None,
        copy_annotation_classes: Optional[bool] = True,
        copy_settings: Optional[bool] = True,
        copy_workflow: Optional[bool] = False,
        copy_contributors: Optional[bool] = False,
    ):
        """Create a new project in the team using annotation classes and settings from from_project.

        :param project_name: new project's name
        :type project_name: str

        :param from_project: the name of the project being used for duplication
        :type from_project: str

        :param project_description: the new project's description. If None, from_project's
                                    description will be used
        :type project_description: str

        :param copy_annotation_classes: enables copying annotation classes
        :type copy_annotation_classes: bool

        :param copy_settings: enables copying project settings
        :type copy_settings: bool

        :param copy_workflow: Deprecated
        :type copy_workflow: bool

        :param copy_contributors: enables copying project contributors
        :type copy_contributors: bool

        :return: dict object metadata of the new project
        :rtype: dict
        """
        if copy_workflow:
            warnings.warn(
                DeprecationWarning(
                    "The “copy_workflow” parameter is deprecated. Please use the “set_project_steps” function instead."
                )
            )
        response = self.controller.projects.get_metadata(
            self.controller.get_project(from_project),
            include_annotation_classes=copy_annotation_classes,
            include_settings=copy_settings,
            include_contributors=copy_contributors,
        )
        response.raise_for_status()
        project: entities.ProjectEntity = response.data

        project_copy = copy.copy(project)
        if project_copy.type in (
            constants.ProjectType.VECTOR,
            constants.ProjectType.PIXEL,
        ):
            project_copy.upload_state = constants.UploadState.INITIAL
        if project_description:
            project_copy.description = project_description
        else:
            project_copy.description = project.description
        project_copy.name = project_name
        create_response = self.controller.projects.create(project_copy)
        create_response.raise_for_status()
        new_project = create_response.data
        if copy_contributors:
            logger.info(f"Cloning contributors from {from_project} to {project_name}.")
            self.controller.projects.add_contributors(
                self.controller.team, new_project, project.contributors
            )
        if copy_annotation_classes:
            logger.info(
                f"Cloning annotation classes from {from_project} to {project_name}."
            )
            classes_response = self.controller.annotation_classes.create_multiple(
                new_project, project.classes
            )
            classes_response.raise_for_status()
            project.classes = classes_response.data
        response = self.controller.projects.get_metadata(
            new_project,
            include_settings=copy_settings,
            include_contributors=copy_contributors,
            include_annotation_classes=copy_annotation_classes,
            include_complete_image_count=True,
        )

        if response.errors:
            raise AppException(response.errors)
        data = ProjectSerializer(response.data).serialize()
        if data.get("users"):
            for contributor in data["users"]:
                contributor[
                    "user_role"
                ] = self.controller.service_provider.get_role_name(
                    new_project, contributor["user_role"]
                )
        return data

    def create_folder(self, project: NotEmptyStr, folder_name: NotEmptyStr):
        """
        Create a new folder in the project.

        :param project: project name
        :type project: str

        :param folder_name: the new folder's name
        :type folder_name: str

        :return: dict object metadata the new folder
        :rtype: dict
        """

        project = self.controller.get_project(project)
        folder = entities.FolderEntity(name=folder_name)
        res = self.controller.folders.create(project, folder)
        if res.data:
            folder = res.data
            logger.info(f"Folder {folder.name} created in project {project.name}")
            return FolderSerializer(folder).serialize(
                exclude={"completedCount", "is_root"}
            )
        if res.errors:
            raise AppException(res.errors)

    def delete_project(self, project: Union[NotEmptyStr, dict]):
        """Deletes the project

        :param project: project name
        :type project: str
        """
        name = project
        if isinstance(project, dict):
            name = project["name"]
        self.controller.projects.delete(name=name)

    def rename_project(self, project: NotEmptyStr, new_name: NotEmptyStr):
        """Renames the project

        :param project: project name
        :type project: str

        :param new_name: project's new name
        :type new_name: str
        """
        old_name = project
        project = self.controller.get_project(old_name)  # noqa
        project.name = new_name
        response = self.controller.projects.update(project)
        if response.errors:
            raise AppException(response.errors)
        logger.info(
            "Successfully renamed project %s to %s.", old_name, response.data.name
        )
        return ProjectSerializer(response.data).serialize()

    def get_folder_metadata(self, project: NotEmptyStr, folder_name: NotEmptyStr):
        """Returns folder metadata

        :param project: project name
        :type project: str

        :param folder_name: folder's name
        :type folder_name: str

        :return: metadata of folder
        :rtype: dict
        """
        project, folder = self.controller.get_project_folder((project, folder_name))
        if not folder:
            raise AppException("Folder not found.")
        return BaseSerializer(folder).serialize(exclude={"completedCount", "is_root"})

    def delete_folders(self, project: NotEmptyStr, folder_names: List[NotEmptyStr]):
        """Delete folder in project.

        :param project: project name
        :type project: str

        :param folder_names: to be deleted folders' names
        :type folder_names: list of strs
        """
        project = self.controller.get_project(project)
        folders = self.controller.folders.list(project).data
        folders_to_delete = [
            folder for folder in folders if folder.name in folder_names
        ]
        res = self.controller.folders.delete_multiple(
            project=project, folders=folders_to_delete
        )
        if res.errors:
            raise AppException(res.errors)
        logger.info(f"Folders {folder_names} deleted in project {project.name}")

    def search_folders(
        self,
        project: NotEmptyStr,
        folder_name: Optional[NotEmptyStr] = None,
        status: Optional[Union[FOLDER_STATUS, List[FOLDER_STATUS]]] = None,
        return_metadata: Optional[bool] = False,
    ):
        """Folder name based case-insensitive search for folders in project.

        :param project: project name
        :type project: str

        :param folder_name: the new folder's name
        :type folder_name: str. If  None, all the folders in the project will be returned.

        :param status:  search folders via status. If None, all folders will be returned. \n
            Available statuses are::

                     * NotStarted
                     * InProgress
                     * Completed
                     * OnHold
        :type status: str or list of str

        :param return_metadata: return metadata of folders instead of names
        :type return_metadata: bool

        :return: folder names or metadatas
        :rtype: list of strs or dicts

        """

        project = self.controller.get_project(project)
        condition = EmptyCondition()
        if folder_name:
            condition &= Condition("name", folder_name, EQ)
        if return_metadata:
            condition &= Condition("includeUsers", return_metadata, EQ)
        if status:
            if isinstance(status, list):
                status_condition = [constants.FolderStatus(i).value for i in status]
            else:
                status_condition = constants.FolderStatus(status).value
            condition &= Condition("status", status_condition, EQ)
        response = self.controller.folders.list(project, condition)
        if response.errors:
            raise AppException(response.errors)
        data = response.data
        if return_metadata:
            return [
                FolderSerializer(folder).serialize(
                    exclude={"completedCount", "is_root"}
                )
                for folder in data
                if not folder.is_root
            ]
        return [folder.name for folder in data if not folder.is_root]

    def get_project_metadata(
        self,
        project: Union[NotEmptyStr, dict],
        include_annotation_classes: Optional[bool] = False,
        include_settings: Optional[bool] = False,
        include_workflow: Optional[bool] = False,
        include_contributors: Optional[bool] = False,
        include_complete_item_count: Optional[bool] = False,
        include_custom_fields: Optional[bool] = False,
    ):
        """Returns project metadata

        :param project: project name
        :type project: str

        :param include_annotation_classes: enables project annotation classes output under
                                           the key "annotation_classes"
        :type include_annotation_classes: bool

        :param include_settings: enables project settings output under
                                 the key "settings"
        :type include_settings: bool

        :param include_workflow: Returns workflow metadata
        :type include_workflow: bool

        :param include_contributors: enables project contributors output under
                                 the key "contributors"
        :type include_contributors: bool

        :param include_complete_item_count: enables project complete item count output under
                                 the key "completed_items_count"
        :type include_complete_item_count: bool

        :param include_custom_fields: include custom fields that have been created for the project.
        :type include_custom_fields: bool

        :return: metadata of project
        :rtype: dict


        Request Example:
        ::

            client.get_project_metadata(
                project="Medical Annotations",
                include_workflow=True,
                include_custom_fields=True
            )


        Response Example:
        ::

            {
                "createdAt": "2025-02-04T12:04:01+00:00",
                "updatedAt": "2024-02-04T12:04:01+00:00",
                "id": 902174,
                "team_id": 233435,
                "name": "Medical Annotations",
                "type": "Vector",
                "description": "DESCRIPTION",
                "instructions_link": None,
                "creator_id": "ecample@email.com",
                "entropy_status": 1,
                "sharing_status": None,
                "status": "NotStarted",
                "folder_id": 1191383,
                "workflow_id": 1,
                "workflow": {
                    "createdAt": "2024-09-03T12:48:09+00:00",
                    "updatedAt": "2024-09-03T12:48:09+00:00",
                    "id": 1,
                    "name": "System workflow",
                    "type": "system",
                    "description": "This workflow is generated by the system, and prevents annotators from completing items.",
                    "raw_config": {"roles": ["Annotator", "QA"], ...}
                },
                "upload_state": "INITIAL",
                "users": [],
                "contributors": [],
                "settings": [],
                "classes": [],
                "item_count": None,
                "completed_items_count": None,
                "root_folder_completed_items_count": None,
                "custom_fields": {
                    "Notes": "Something",
                    "Ann Quality threshold": 80,
                    "Tag": ["Tag1", "Tag2", "Tag3"],
                    "Due date": 1738281600.0,
                    "Other_Custom_Field": None,
                }
            }
        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.get_project(project_name)
        response = self.controller.projects.get_metadata(
            project,
            include_annotation_classes,
            include_settings,
            include_workflow,
            include_contributors,
            include_complete_item_count,
            include_custom_fields,
        )
        if response.errors:
            raise AppException(response.errors)
        data = ProjectSerializer(response.data).serialize()
        if data.get("users"):
            for contributor in data["users"]:
                contributor[
                    "user_role"
                ] = self.controller.service_provider.get_role_name(
                    response.data, contributor["user_role"]
                )
        return data

    def get_project_settings(self, project: Union[NotEmptyStr, dict]):
        """Gets project's settings.

        Return value example: [{ "attribute" : "Brightness", "value" : 10, ...},...]

        :param project: project name or metadata
        :type project: str or dict

        :return: project settings
        :rtype: list of dicts
        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.projects.get_by_name(project_name).data
        settings = self.controller.projects.list_settings(project).data
        settings = [
            SettingsSerializer(attribute.dict()).serialize() for attribute in settings
        ]
        return settings

    def get_project_steps(self, project: Union[str, dict]):
        """Gets project's steps.

        Return value example: [{ "step" : <step_num>, "className" : <annotation_class>, "tool" : <tool_num>, ...},...]

        :param project: project name or metadata
        :type project: str or dict

        :return: A list of step dictionaries,
            or a dictionary containing both steps and their connections (for Keypoint workflows).
        :rtype: list of dicts or dict

        Response Example for General Annotation Project:
        ::

            [
                {
                    "step": 1,
                    "className": "Anatomy",
                    "tool": 2,
                    "attribute": [
                        {
                            "attribute": {
                                "name": "Lung",
                                "attribute_group": {"name": "Organs"}
                            }
                        }
                    ]
                }
            ]

        Response Example for Keypoint Annotation Project:
        ::

            {
              "steps": [
                {
                  "step": 1,
                  "className": "Left Shoulder",
                  "class_id": "1",
                  "attribute": [
                    {
                            "attribute": {
                                "id": 123,
                                "group_id": 12
                            }
                        }
                  ]
                },
                {
                  "step": 2,
                  "class_id": "2",
                  "className": "Right Shoulder",
                }
              ],
              "connections": [
                [1, 2]
              ]
            }
        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.get_project(project_name)
        steps = self.controller.projects.list_steps(project)
        if steps.errors:
            raise AppException(steps.errors)
        return steps.data

    def search_annotation_classes(
        self, project: Union[NotEmptyStr, dict], name_contains: Optional[str] = None
    ):
        """Searches annotation classes by name_prefix (case-insensitive)

        :param project: project name
        :type project: str

        :param name_contains:  search string. Returns those classes,
         where the given string is found anywhere within its name. If None, all annotation classes will be returned.
        :type name_contains: str

        :return: annotation classes of the project
        :rtype: list of dicts
        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.get_project(project_name)
        condition = Condition("project_id", project.id, EQ)
        if name_contains:
            condition &= Condition("name", name_contains, EQ) & Condition(
                "pattern", True, EQ
            )
        response = self.controller.annotation_classes.list(condition)
        if response.errors:
            raise AppException(response.errors)
        return BaseSerializer.serialize_iterable(response.data)

    def set_project_status(self, project: NotEmptyStr, status: PROJECT_STATUS):
        """Set project status

        :param project: project name
        :type project: str

        :param status: status to set.

            Available statuses are::

                 * NotStarted
                 * InProgress
                 * Returned
                 * Completed
                 * OnHold

        :type status: str
        """
        project = self.controller.get_project(name=project)
        project.status = constants.ProjectStatus(status).value
        response = self.controller.projects.update(project)
        if response.errors:
            raise AppException(f"Failed to change {project.name} status.")
        logger.info(f"Successfully updated {project.name} status to {status}")

    def set_project_custom_field(
        self, project: Union[NotEmptyStr, int], custom_field_name: str, value: Any
    ):
        """Sets or updates the value of a custom field for a specified project.

        :param project: The name or ID of the project for which the custom field should be set or updated.
        :type project: str or int

        :param custom_field_name: The name of the custom field to update or set.
         This field must already exist for the project.
        :type custom_field_name: str

        :param value: The value assigned to the custom field, with the type depending on the field's configuration.
            Multi-select fields must be provided as a list of strings (e.g., ["Tag1", "Tag2"]).
            Date fields must be in Unix timestamp format (e.g., "1738281600").
            Other fields (e.g., text, numbers) should match the expected type as defined in the project schema.
        :type value: Any

        Request Example:
        ::

            client.set_project_custom_field(
                project="Medical Annotations",
                custom_field_name="due_date",
                value=1738671238.759,
            )
        """
        project = (
            self.controller.get_project_by_id(project).data
            if isinstance(project, int)
            else self.controller.get_project(project)
        )
        self.controller.work_management.set_custom_field_value(
            entity_id=project.id,
            field_name=custom_field_name,
            value=value,
            entity=CustomFieldEntityEnum.PROJECT,
            parent_entity=CustomFieldEntityEnum.TEAM,
        )

    def set_folder_status(
        self, project: NotEmptyStr, folder: NotEmptyStr, status: FOLDER_STATUS
    ):
        """Set folder status

        :param project: project name
        :type project: str

        :param folder: folder name
        :type folder: str

        :param status: status to set. \n
            Available statuses are::

                     * NotStarted
                     * InProgress
                     * Completed
                     * OnHold
        :type status: str
        """
        project, folder = self.controller.get_project_folder((project, folder))
        folder.status = constants.FolderStatus(status).value
        response = self.controller.update(project, folder)
        if response.errors:
            raise AppException(f"Failed to change {project.name}/{folder.name} status.")
        logger.info(
            f"Successfully updated {project.name}/{folder.name} status to {status}"
        )

    def set_project_default_image_quality_in_editor(
        self,
        project: Union[NotEmptyStr, dict],
        image_quality_in_editor: Optional[str],
    ):
        """Sets project's default image quality in editor setting.

        :param project: project name or metadata
        :type project: str or dict
        :param image_quality_in_editor: new setting value, should be "original" or "compressed"
        :type image_quality_in_editor: str
        """
        project_name, _ = extract_project_folder(project)
        image_quality_in_editor = ImageQuality(image_quality_in_editor).value
        project = self.controller.get_project(project_name)
        response = self.controller.projects.set_settings(
            project=project,
            settings=[{"attribute": "ImageQuality", "value": image_quality_in_editor}],
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def pin_image(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: str,
        pin: Optional[bool] = True,
    ):
        """Pins (or unpins) image

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param pin: sets to pin if True, else unpins image
        :type pin: bool
        """
        project, folder = self.controller.get_project_folder_by_path(project)
        items = self.controller.items.list_items(project, folder, name=image_name)
        item = next(iter(items), None)
        if not items:
            raise AppException("Item not found.")
        item.is_pinned = int(pin)
        self.controller.items.update(project=project, item=item)

    def delete_items(self, project: str, items: Optional[List[str]] = None):
        """Delete items in a given project.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param items: to be deleted items' names. If None, all the items will be deleted
        :type items: list of str
        """
        project, folder = self.controller.get_project_folder_by_path(project)
        response = self.controller.items.delete(
            project=project, folder=folder, item_names=items
        )
        if response.errors:
            raise AppException(response.errors)

    def assign_items(
        self, project: Union[NotEmptyStr, dict], items: List[str], user: str
    ):
        """Assigns items  to a user. The assignment role, QA or Annotator, will
        be deduced from the user's role in the project. The type of the objects` image, video or text
        will be deduced from the project type. With SDK, the user can be
        assigned to a role in the project with the share_project function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param items: list of items to assign
        :type items: list of str

        :param user: user email
        :type user: str
        """

        project, folder = self.controller.get_project_folder_by_path(project)
        response = self.controller.projects.assign_items(
            project, folder, item_names=items, user=user
        )

        if response.errors:
            raise AppException(response.errors)

    def unassign_items(
        self, project: Union[NotEmptyStr, dict], items: List[NotEmptyStr]
    ):
        """Removes assignment of given items for all assignees. With SDK,
        the user can be assigned to a role in the project with the share_project
        function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param items: list of items to unassign
        :type items: list of str
        """
        project, folder = self.controller.get_project_folder_by_path(project)
        response = self.controller.projects.un_assign_items(
            project, folder, item_names=items
        )
        if response.errors:
            raise AppException(response.errors)

    def unassign_folder(self, project_name: NotEmptyStr, folder_name: NotEmptyStr):
        """Removes assignment of given folder for all assignees.
        With SDK, the user can be assigned to a role in the project
        with the share_project function.

        :param project_name: project name
        :type project_name: str
        :param folder_name: folder name to remove assignees
        :type folder_name: str
        """
        response = self.controller.un_assign_folder(
            project_name=project_name, folder_name=folder_name
        )
        if response.errors:
            raise AppException(response.errors)

    def assign_folder(
        self,
        project_name: NotEmptyStr,
        folder_name: NotEmptyStr,
        users: List[NotEmptyStr],
    ):
        """Assigns folder to users. With SDK, the user can be
        assigned to a role in the project with the share_project function.

        :param project_name: project name or metadata of the project
        :type project_name: str or dict
        :param folder_name: folder name to assign
        :type folder_name: str
        :param users: list of user emails
        :type users: list of str
        """

        response = self.controller.projects.get_by_name(name=project_name)
        if response.errors:
            raise AppException(response.errors)
        project = response.data
        response = self.controller.projects.get_metadata(
            project=project, include_contributors=True
        )

        if response.errors:
            raise AppException(response.errors)

        contributors = response.data.users
        verified_users = [i.user_id for i in contributors]
        verified_users = set(users).intersection(set(verified_users))
        unverified_contributor = set(users) - verified_users

        for user in unverified_contributor:
            logger.warning(
                f"Skipping {user} from assignees. {user} is not a verified contributor for the {project_name}"
            )

        if not verified_users:
            return
        project, folder = self.controller.get_project_folder(
            (project_name, folder_name)
        )
        response = self.controller.folders.assign_users(
            project=project,
            folder=folder,
            users=list(verified_users),
        )

        if response.errors:
            raise AppException(response.errors)

    def upload_images_from_folder_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        folder_path: Union[NotEmptyStr, Path],
        extensions: Optional[
            Union[List[NotEmptyStr], Tuple[NotEmptyStr]]
        ] = constants.DEFAULT_IMAGE_EXTENSIONS,
        annotation_status: Optional[str] = None,
        from_s3_bucket=None,
        exclude_file_patterns: Optional[
            Iterable[NotEmptyStr]
        ] = constants.DEFAULT_FILE_EXCLUDE_PATTERNS,
        recursive_subfolders: Optional[bool] = False,
        image_quality_in_editor: Optional[str] = None,
    ):
        """Uploads all images with given extensions from folder_path to the project.
        Sets status of all the uploaded images to set_status if it is not None.

        If an image with existing name already exists in the project it won't be uploaded,
        and its path will be appended to the third member of return value of this
        function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str or dict

        :param folder_path: from which folder to upload the images
        :type folder_path: Path-like (str or Path)

        :param extensions: tuple or list of filename extensions to include from folder
        :type extensions: tuple or list of strs

        :param annotation_status: the annotation status of the item within the current project workflow.
                                  If None, the status will be set to the start status of the project workflow.
        :type annotation_status: str

        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str

        :param exclude_file_patterns: filename patterns to exclude from uploading,
                default value is to exclude SuperAnnotate export related ["___save.png", "___fuse.png"]
        :type exclude_file_patterns: list or tuple of strs

        :param recursive_subfolders: enable recursive subfolder parsing
        :type recursive_subfolders: bool

        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
                Can be either "compressed" or "original".
                If None then the default value in project settings will be used.
        :type image_quality_in_editor: str

        :return: uploaded, could-not-upload, existing-images filepaths
        :rtype: tuple (3 members) of list of strs
        """

        project_name, folder_name = extract_project_folder(project)
        if annotation_status is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “keep_status” parameter is deprecated. "
                    "Please use the “set_annotation_statuses” function instead."
                )
            )
        if recursive_subfolders:
            logger.info(
                "When using recursive subfolder parsing same name images"
                " in different subfolders will overwrite each other."
            )
        if not isinstance(extensions, (list, tuple)):
            print(extensions)
            raise AppException(
                "extensions should be a list or a tuple in upload_images_from_folder_to_project"
            )
        if len(extensions) < 1:
            return [], [], []

        if exclude_file_patterns:
            exclude_file_patterns = list(exclude_file_patterns) + list(
                constants.DEFAULT_FILE_EXCLUDE_PATTERNS
            )
            exclude_file_patterns = list(set(exclude_file_patterns))

        project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")

        logger.info(
            "Uploading all images with extensions %s from %s to project %s. Excluded file patterns are: %s.",
            extensions,
            folder_path,
            project_folder_name,
            exclude_file_patterns,
        )
        project = self.controller.get_project(project_name)
        use_case = self.controller.upload_images_from_folder_to_project(
            project=project,
            folder_name=folder_name,
            folder_path=folder_path,
            extensions=extensions,
            annotation_status=annotation_status,
            from_s3_bucket=from_s3_bucket,
            exclude_file_patterns=exclude_file_patterns,
            recursive_sub_folders=recursive_subfolders,
            image_quality_in_editor=image_quality_in_editor,
        )
        images_to_upload, duplicates = use_case.images_to_upload
        if len(duplicates):
            logger.warning(
                "%s already existing images found that won't be uploaded.",
                len(duplicates),
            )
        logger.info(
            "Uploading %s images to project %s.",
            len(images_to_upload),
            project_folder_name,
        )
        if not images_to_upload:
            return [], [], duplicates
        if use_case.is_valid():
            with tqdm(
                total=len(images_to_upload), desc="Uploading images"
            ) as progress_bar:
                for _ in use_case.execute():
                    progress_bar.update(1)
            return use_case.data
        raise AppException(use_case.response.errors)

    def download_image_annotations(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: NotEmptyStr,
        local_dir_path: Union[str, Path],
    ):
        """Downloads annotations of the image (JSON and mask if pixel type project)
        to local_dir_path.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param image_name: image name
        :type image_name: str

        :param local_dir_path: local directory path to download to
        :type local_dir_path: Path-like (str or Path)

        :return: paths of downloaded annotations
        :rtype: tuple
        """

        project, folder = self.controller.get_project_folder_by_path(project)
        res = self.controller.annotations.download_image_annotations(
            project=project,
            folder=folder,
            image_name=image_name,
            destination=local_dir_path,
        )
        if res.errors:
            raise AppException(res.errors)
        return res.data

    def get_exports(
        self, project: NotEmptyStr, return_metadata: Optional[bool] = False
    ):
        """Get all prepared exports of the project.

        :param project: project name
        :type project: str

        :param return_metadata: return metadata of images instead of names
        :type return_metadata: bool

        :return: names or metadata objects of the all prepared exports of the project
        :rtype: list of strs or dicts
        """
        response = self.controller.get_exports(
            project_name=project, return_metadata=return_metadata
        )
        return response.data

    def prepare_export(
        self,
        project: Union[NotEmptyStr, dict],
        folder_names: Optional[List[NotEmptyStr]] = None,
        annotation_statuses: Optional[List[str]] = None,
        include_fuse: Optional[bool] = False,
        only_pinned=False,
        **kwargs,
    ):
        """Prepare annotations and classes.json for export. Original and fused images for images with
        annotations can be included with include_fuse flag.

        :param project: project name
        :type project: str

        :param folder_names: names of folders to include in the export. If None, whole project will be exported
        :type folder_names: list of str

        :param annotation_statuses: images with which status to include, if None,
               ["NotStarted", "InProgress", "QualityCheck", "Returned", "Completed", "Skipped"]  will be chosen
               list elements should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_statuses: list of strs

        :param include_fuse: enables fuse images in the export
        :type include_fuse: bool

        :param only_pinned: enable only pinned output in export. This option disables all other types of output.
        :type only_pinned: bool

        :param kwargs: Arbitrary keyword arguments:

             - integration_name: The name of the integration within the platform that is being used.
             - format: The format in which the data will be exported in multimodal projects.
               The data can be exported in CSV, JSON, or JSONL format. If None, the data will be exported
               in the default JSON format.
        :return: metadata object of the prepared export
        :rtype: dict

        Request Example:
        ::

            client = SAClient()

            export = client.prepare_export(
                project = "Project Name",
                folder_names = ["Folder 1", "Folder 2"],
                annotation_statuses = ["Completed","QualityCheck"],
                format = "CSV"
            )

            client.download_export("Project Name", export, "path_to_download")
        """
        project_name, folder_name = extract_project_folder(project)
        if folder_names is None:
            folders = [folder_name] if folder_name else []
        else:
            folders = folder_names
        integration_name = kwargs.get("integration_name")
        integration_id = None
        if integration_name:
            for integration in self.controller.integrations.list().data:
                if integration.name == integration_name:
                    integration_id = integration.id
                    break
            else:
                raise AppException("Integration not found.")
        _export_type = None
        export_type = kwargs.get("format")
        if export_type:
            export_type = export_type.lower()
            if export_type == "csv":
                _export_type = 3
            elif export_type == "jsonl":
                _export_type = 4
        response = self.controller.prepare_export(
            project_name=project_name,
            folder_names=folders,
            include_fuse=include_fuse,
            only_pinned=only_pinned,
            annotation_statuses=annotation_statuses,
            integration_id=integration_id,
            export_type=_export_type,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_videos_from_folder_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        folder_path: Union[NotEmptyStr, Path],
        extensions: Optional[
            Union[Tuple[NotEmptyStr], List[NotEmptyStr]]
        ] = constants.DEFAULT_VIDEO_EXTENSIONS,
        exclude_file_patterns: Optional[List[NotEmptyStr]] = (),
        recursive_subfolders: Optional[bool] = False,
        target_fps: Optional[int] = None,
        start_time: Optional[float] = 0.0,
        end_time: Optional[float] = None,
        annotation_status: str = None,
        image_quality_in_editor: Optional[IMAGE_QUALITY] = None,
    ):
        """Uploads image frames from all videos with given extensions from folder_path to the project.
        Sets status of all the uploaded images to set_status if it is not None.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param folder_path: from which folder to upload the videos
        :type folder_path: Path-like (str or Path)

        :param extensions: tuple or list of filename extensions to include from folder
        :type extensions: tuple or list of strs

        :param exclude_file_patterns: filename patterns to exclude from uploading
        :type exclude_file_patterns: listlike of strs

        :param recursive_subfolders: enable recursive subfolder parsing
        :type recursive_subfolders: bool

        :param target_fps: how many frames per second need to extract from the video (approximate).
                           If None, all frames will be uploaded
        :type target_fps: float

        :param start_time: Time (in seconds) from which to start extracting frames
        :type start_time: float

        :param end_time: Time (in seconds) up to which to extract frames. If None up to end
        :type end_time: float

        :param annotation_status:  the annotation status of the item within the current project workflow.
                                   If None, the status will be set to the start status of the project workflow.
        :type annotation_status: str

        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
            Can be either "compressed" or "original".
            If None then the default value in project settings will be used.
        :type image_quality_in_editor: str

        :return: uploaded and not-uploaded video frame images' filenames
        :rtype: tuple of list of strs
        """

        project_name, folder_name = extract_project_folder(project)
        if annotation_status is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “keep_status” parameter is deprecated. "
                    "Please use the “set_annotation_statuses” function instead."
                )
            )
        video_paths = []
        for extension in extensions:
            if not recursive_subfolders:
                video_paths += list(Path(folder_path).glob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    video_paths += list(
                        Path(folder_path).glob(f"*.{extension.upper()}")
                    )
            else:
                logger.warning(
                    "When using recursive subfolder parsing same name videos "
                    "in different subfolders will overwrite each other."
                )
                video_paths += list(Path(folder_path).rglob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    video_paths += list(
                        Path(folder_path).rglob(f"*.{extension.upper()}")
                    )

        video_paths = [str(path) for path in video_paths]
        response = self.controller.upload_videos(
            project_name=project_name,
            folder_name=folder_name,
            paths=video_paths,
            target_fps=target_fps,
            start_time=start_time,
            exclude_file_patterns=exclude_file_patterns,
            end_time=end_time,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_video_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        video_path: Union[NotEmptyStr, Path],
        target_fps: Optional[int] = None,
        start_time: Optional[float] = 0.0,
        end_time: Optional[float] = None,
        annotation_status: Optional[str] = None,
        image_quality_in_editor: Optional[IMAGE_QUALITY] = None,
    ):
        """Uploads image frames from video to platform. Uploaded images will have
        names "<video_name>_<frame_no>.jpg".

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param video_path: video to upload
        :type video_path: Path-like (str or Path)

        :param target_fps: how many frames per second need to extract from the video (approximate).
                           If None, all frames will be uploaded
        :type target_fps: float

        :param start_time: Time (in seconds) from which to start extracting frames
        :type start_time: float

        :param end_time: Time (in seconds) up to which to extract frames. If None up to end
        :type end_time: float

        :param annotation_status:  the annotation status of the item within the current project workflow.
                                   If None, the status will be set to the start status of the project workflow.
        :type annotation_status: str

        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
                Can be either "compressed" or "original".
                If None then the default value in project settings will be used.
        :type image_quality_in_editor: str

        :return: filenames of uploaded images
        :rtype: list of strs
        """

        project_name, folder_name = extract_project_folder(project)
        if annotation_status is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “keep_status” parameter is deprecated. "
                    "Please use the “set_annotation_statuses” function instead."
                )
            )
        response = self.controller.upload_videos(
            project_name=project_name,
            folder_name=folder_name,
            paths=[video_path],
            target_fps=target_fps,
            start_time=start_time,
            end_time=end_time,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def create_annotation_class(
        self,
        project: Union[Project, NotEmptyStr],
        name: NotEmptyStr,
        color: NotEmptyStr,
        attribute_groups: Optional[List[AttributeGroup]] = None,
        class_type: str = "object",
    ):
        """Create annotation class in project

        :param project: project name
        :type project: str

        :param name: name for the class
        :type name: str

        :param color: RGB hex color value, e.g., "#F9E0FA"
        :type color: str

        :param attribute_groups:  list of attribute group dicts.
            The values for the "group_type" key are
            ::

                * radio
                * checklist
                * checklist
                * text
                * numeric
                * ocr

            `ocr` and `group_type` keys are only available for Vector projects.
            Mandatory keys for each attribute group are::

              - "name"
        :type attribute_groups: list of dicts

        :param class_type: class type. Should be either "object" or "tag". Document project type can also have "relationship" type of classes.
        :type class_type: str

        :return: new class metadata
        :rtype: dict

        Request Example:
        ::

            attributes_list = [
                {
                    "group_type": "radio",
                    "name": "Vehicle",
                    "attributes": [
                       {
                           "name": "Car"
                       },
                       {
                           "name": "Track"
                       },
                       {
                           "name": "Bus"
                       }
                   ],
                   "default_value": "Car"
               },
               {
                   "group_type": "checklist",
                   "name": "Color",
                   "attributes": [
                       {
                           "name": "Yellow"
                       },
                       {
                           "name": "Black"
                       },
                       {
                           "name": "White"
                       }
                   ],
                   "default_value": ["Yellow", "White"]
               },
               {
                   "group_type": "text",
                   "name": "Timestamp"
               },
               {
                   "group_type": "numeric",
                   "name": "Description"
               }
            ]
            client.create_annotation_class(
               project="Image Project",
               name="Example Class",
               color="#F9E0FA",
               attribute_groups=attributes_list
            )

        """
        if isinstance(project, Project):
            project = project.dict()
        attribute_groups = (
            list(map(lambda x: x.dict(), attribute_groups)) if attribute_groups else []
        )
        try:
            annotation_class = AnnotationClassEntity(
                name=name,
                color=color,  # noqa
                attribute_groups=attribute_groups,
                type=class_type,  # noqa
            )
        except ValidationError as e:
            raise AppException(wrap_error(e))
        project = self.controller.projects.get_by_name(project).data
        if (
            project.type != ProjectType.DOCUMENT
            and annotation_class.type == ClassTypeEnum.RELATIONSHIP
        ):
            raise AppException(
                f"{annotation_class.type.name} class type is not supported in {project.type.name} project."
            )
        response = self.controller.annotation_classes.create(
            project=project, annotation_class=annotation_class
        )
        if response.errors:
            raise AppException(response.errors)
        return BaseSerializer(response.data).serialize(exclude_unset=True)

    def delete_annotation_class(
        self, project: NotEmptyStr, annotation_class: Union[dict, NotEmptyStr]
    ):
        """Deletes annotation class from project

        :param project: project name
        :type project: str

        :param annotation_class: annotation class name or  metadata
        :type annotation_class: str or dict
        """

        if isinstance(annotation_class, str):
            try:
                annotation_class = AnnotationClassEntity(
                    name=annotation_class,
                    color="#ffffff",  # noqa Random, just need to serialize
                )
            except ValidationError as e:
                raise AppException(wrap_error(e))
        else:
            annotation_class = AnnotationClassEntity(**annotation_class)
        project = self.controller.projects.get_by_name(project).data

        self.controller.annotation_classes.delete(
            project=project, annotation_class=annotation_class
        )

    def download_annotation_classes_json(
        self, project: NotEmptyStr, folder: Union[str, Path]
    ):
        """Downloads project classes.json to folder

        :param project: project name
        :type project: str

        :param folder: folder to download to
        :type folder: Path-like (str or Path)

        :return: path of the download file
        :rtype: str
        """

        project = self.controller.projects.get_by_name(project).data
        logger.info(
            f"Downloading classes.json from project {project.name} to folder {str(folder)}."
        )
        response = self.controller.annotation_classes.list(
            condition=Condition("project_id", project.id, EQ)
        )
        if response.errors:
            raise AppException(response.errors)
        classes = BaseSerializer.serialize_iterable(response.data)
        json_path = f"{folder}/classes.json"
        with open(json_path, "w") as f:
            json.dump(classes, f, indent=4)
        return json_path

    def create_annotation_classes_from_classes_json(
        self,
        project: Union[NotEmptyStr, dict],
        classes_json: Union[List[AnnotationClassEntity], str, Path],
        from_s3_bucket=False,
    ):
        """Creates annotation classes in project from a SuperAnnotate format
        annotation classes.json.

        :param project: project name
        :type project: str

        :param classes_json: JSON itself or path to the JSON file
        :type classes_json: list or Path-like (str or Path)

        :param from_s3_bucket: AWS S3 bucket to use. If None then classes_json is in local filesystem
        :type from_s3_bucket: str

        :return: list of created annotation class metadatas
        :rtype: list of dicts
        """
        if isinstance(classes_json, (str, Path)):
            if from_s3_bucket:
                from_session = boto3.Session()
                from_s3 = from_session.resource("s3")
                file = io.BytesIO()
                from_s3_object = from_s3.Object(from_s3_bucket, classes_json)
                from_s3_object.download_fileobj(file)
                file.seek(0)
                classes_json = json.load(file)
            else:
                with open(classes_json, encoding="utf-8") as f:
                    classes_json = json.load(f)
        try:
            annotation_classes = parse_obj_as(List[AnnotationClassEntity], classes_json)
        except ValidationError as _:
            raise AppException("Couldn't validate annotation classes.")
        project = self.controller.projects.get_by_name(project).data
        response = self.controller.annotation_classes.create_multiple(
            project=project,
            annotation_classes=annotation_classes,
        )
        if response.errors:
            raise AppException(response.errors)
        return [BaseSerializer(i).serialize(exclude_unset=True) for i in response.data]

    def download_export(
        self,
        project: Union[NotEmptyStr, dict],
        export: Union[NotEmptyStr, dict],
        folder_path: Union[str, Path],
        extract_zip_contents: Optional[bool] = True,
        to_s3_bucket=None,
    ):
        """Download prepared export.

        :param project: project name
        :type project: str

        :param export: export name
        :type export: str or dict

        :param folder_path: where to download the export
        :type folder_path: Path-like (str or Path)

        :param extract_zip_contents: if False then a zip file will be downloaded,
         if True the zip file will be extracted at folder_path
        :type extract_zip_contents: bool

        :param to_s3_bucket: AWS S3 bucket to use for download. If None then folder_path is in local filesystem.
        :type to_s3_bucket: Bucket object
        """
        project_name, _ = extract_project_folder(project)
        export_name = export["name"] if isinstance(export, dict) else export

        response = self.controller.download_export(
            project_name=project_name,
            export_name=export_name,
            folder_path=folder_path,
            extract_zip_contents=extract_zip_contents,
            to_s3_bucket=to_s3_bucket,
        )
        if response.errors:
            raise AppException(response.errors)

    def set_project_steps(
        self,
        project: Union[NotEmptyStr, dict],
        steps: List[dict],
        connections: List[List[int]] = None,
    ):
        """Sets project's steps.

        :param project: project name or metadata
        :type project: str or dict

        :param steps: new workflow list of dicts
        :type steps: list of dicts

        :param connections: Defines connections between keypoint annotation steps.
            Each inner list specifies a pair of step IDs indicating a connection.
        :type connections: list of dicts

        Request Example for General Annotation Project:
        ::

            sa.set_project_steps(
                project="Medical Annotations",
                steps=[
                    {
                        "step": 1,
                        "className": "Anatomy",
                        "tool": 2,
                        "attribute": [
                            {
                                "attribute": {
                                    "name": "Lung",
                                    "attribute_group": {"name": "Organs"}
                                }
                            }
                        ]
                    }
                ]
            )

        Request Example for Keypoint Annotation Project:
        ::

            sa.set_project_steps(
                project="Pose Estimation Project",
                steps=[
                    {
                        "step": 1,
                        "class_id": 12,
                        "attribute": [
                            {
                                "attribute": {
                                    "id": 123,
                                    "group_id": 12
                                }
                            }
                        ]
                    },
                    {
                        "step": 2,
                        "class_id": 13
                    }
                ],
                connections=[
                    [1, 2]
                ]
            )
        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.get_project(project_name)
        response = self.controller.projects.set_steps(
            project, steps=steps, connections=connections
        )
        if response.errors:
            raise AppException(response.errors)

    def download_image(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: NotEmptyStr,
        local_dir_path: Optional[Union[str, Path]] = "./",
        include_annotations: Optional[bool] = False,
        include_fuse: Optional[bool] = False,
        include_overlay: Optional[bool] = False,
        variant: Optional[str] = "original",
    ):
        """Downloads the image (and annotation if not None) to local_dir_path

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param image_name: image name
        :type image_name: str

        :param local_dir_path: where to download the image
        :type local_dir_path: Path-like (str or Path)

        :param include_annotations: enables annotation download with the image
        :type include_annotations: bool

        :param include_fuse: enables fuse image download with the image
        :type include_fuse: bool

        :param include_overlay: enables overlay image download with the image
        :type include_overlay: bool

        :param variant: which resolution to download, can be 'original' or 'lores'
         (low resolution used in web editor)
        :type variant: str

        :return: paths of downloaded image and annotations if included
        :rtype: tuple
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.download_image(
            project_name=project_name,
            folder_name=folder_name,
            image_name=image_name,
            download_path=str(local_dir_path),
            image_variant=variant,
            include_annotations=include_annotations,
            include_fuse=include_fuse,
            include_overlay=include_overlay,
        )
        if response.errors:
            raise AppException(response.errors)
        logger.info(f"Downloaded image {image_name} to {local_dir_path} ")
        return response.data

    def upload_annotations(
        self,
        project: NotEmptyStr,
        annotations: List[dict],
        keep_status: bool = None,
        *,
        data_spec: Literal["default", "multimodal"] = "default",
    ):
        """Uploads a list of annotation dictionaries to the specified SuperAnnotate project or folder.

        :param project: The project name or folder path where annotations will be uploaded
            (e.g., "project1/folder1").
        :type project: str

        :param annotations: A list of annotation dictionaries formatted according to the SuperAnnotate standards.
        :type annotations: list of dict

        :param keep_status: If False, the annotation status will be automatically updated to "InProgress."
            If True, the current status will remain unchanged.
        :type keep_status: bool, optional

        :param data_spec: Specifies the format for processing and transforming annotations before upload.

            Options are:
                    - default: Retains the annotations in their original format.
                    - multimodal: Converts annotations for multimodal projects, optimizing for
                                     compact and modality-specific data representation.
        :type data_spec: str, optional

        :return: A dictionary containing the results of the upload, categorized into successfully uploaded,
            failed, and skipped annotations.
        :rtype: dict

        Response Example::

            {
               "succeeded": [],
               "failed": [],
               "skipped": []
            }

        Example Usage with JSONL Upload for Multimodal Projects::

            import json
            from pathlib import Path
            from superannotate import SAClient

            annotations_path = Path("annotations.jsonl")
            annotations = []

            # Reading the JSONL file and converting it into a list of dictionaries
            with annotations_path.open("r", encoding="utf-8") as f:
                for line in f:
                    annotations.append(json.loads(line))

            # Initialize the SuperAnnotate client
            sa = SAClient()

            # Call the upload_annotations function
            response = sa.upload_annotations(
                project="project1/folder1",
                annotations=annotations,
                keep_status=True,
                data_spec='multimodal'
            )
        """
        if keep_status is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “keep_status” parameter is deprecated. "
                    "Please use the “set_annotation_statuses” function instead."
                )
            )
        project, folder = self.controller.get_project_folder_by_path(project)
        response = self.controller.annotations.upload_multiple(
            project=project,
            folder=folder,
            annotations=annotations,
            keep_status=keep_status,
            user=self.controller.current_user,
            output_format=data_spec,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_annotations_from_folder_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        folder_path: Union[str, Path],
        from_s3_bucket=None,
        recursive_subfolders: Optional[bool] = False,
        keep_status: Optional[bool] = None,
    ):
        """Finds and uploads all JSON files in the folder_path as annotations to the project.

        The JSON files should follow specific naming convention. For Vector
        projects they should be named "<image_filename>___objects.json" (e.g., if
        image is cats.jpg the annotation filename should be cats.jpg___objects.json), for Pixel projects
        JSON file should be named "<image_filename>___pixel.json" and also second mask
        image file should be present with the name "<image_name>___save.png". In both cases
        image with <image_name> should be already present on the platform.

        Existing annotations will be overwritten.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str or dict

        :param folder_path: from which folder to upload annotations
        :type folder_path: str or dict

        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str

        :param recursive_subfolders: enable recursive subfolder parsing
        :type recursive_subfolders: bool

        :param keep_status:   If False, the annotation status will be automatically
         updated to "InProgress," otherwise the current status will be kept.
        :type keep_status: bool

        :return: paths to annotations uploaded, could-not-upload, missing-images
        :rtype: tuple of list of strs
        """

        project_name, folder_name = extract_project_folder(project)
        if keep_status is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “keep_status” parameter is deprecated. "
                    "Please use the “set_annotation_statuses” function instead."
                )
            )
        project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")

        if recursive_subfolders:
            logger.info(
                "When using recursive subfolder parsing same name annotations in different "
                "subfolders will overwrite each other.",
            )
        logger.info(
            "The JSON files should follow a specific naming convention, matching file names already present "
            "on the platform. Existing annotations will be overwritten"
        )

        annotation_paths = get_annotation_paths(
            folder_path, from_s3_bucket, recursive_subfolders
        )

        logger.info(
            f"Uploading {len(annotation_paths)} annotations from {folder_path} to the project {project_folder_name}."
        )
        project, folder = self.controller.get_project_folder(
            (project_name, folder_name)
        )
        response = self.controller.annotations.upload_from_folder(
            project=project,
            folder=folder,
            user=self.controller.current_user,
            annotation_paths=annotation_paths,  # noqa: E203
            client_s3_bucket=from_s3_bucket,
            folder_path=folder_path,
            keep_status=keep_status,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_image_annotations(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: str,
        annotation_json: Union[str, Path, dict],
        mask: Optional[Union[str, Path, bytes]] = None,
        verbose: Optional[bool] = True,
        keep_status: bool = None,
    ):
        """Upload annotations from JSON (also mask for pixel annotations)
        to the image.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param image_name: image name
        :type image_name: str

        :param annotation_json: annotations in SuperAnnotate format JSON dict or path to JSON file
        :type annotation_json: dict or Path-like (str or Path)

        :param mask: BytesIO object or filepath to mask annotation for pixel projects in SuperAnnotate format
        :type mask: BytesIO or Path-like (str or Path)

        :param verbose: Turns on verbose output logging during the proces.
        :type verbose: bool

        :param keep_status:   If False, the annotation status will be automatically
         updated to "InProgress," otherwise the current status will be kept.
        :type keep_status: bool

        """

        project_name, folder_name = extract_project_folder(project)
        if keep_status is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “keep_status” parameter is deprecated. "
                    "Please use the “set_annotation_statuses” function instead."
                )
            )
        project = self.controller.projects.get_by_name(project_name).data
        if project.type not in constants.ProjectType.images:
            raise AppException(LIMITED_FUNCTIONS[project.type])

        if not mask:
            if not isinstance(annotation_json, dict):
                mask_path = str(annotation_json).replace("___pixel.json", "___save.png")
            else:
                mask_path = f"{image_name}___save.png"
            if os.path.exists(mask_path):
                with open(mask_path, "rb") as f:
                    mask = f.read()
        elif isinstance(mask, str) or isinstance(mask, Path):
            if os.path.exists(mask):
                with open(mask, "rb") as f:
                    mask = f.read()

        if not isinstance(annotation_json, dict):
            if verbose:
                logger.info("Uploading annotations from %s.", annotation_json)
            with open(annotation_json, "rb") as f:
                annotation_json = json.load(f)
        folder = self.controller.get_folder(project, folder_name)
        if not folder:
            raise AppException("Folder not found.")

        items = self.controller.items.list_items(project, folder, name=image_name)
        image = next(iter(items), None)
        if not image:
            raise AppException("Image not found.")

        response = self.controller.annotations.upload_image_annotations(
            project=project,
            folder=folder,
            image=image,
            annotations=annotation_json,
            user=self.controller.current_user,
            mask=mask,
            verbose=verbose,
            keep_status=keep_status,
        )
        if response.errors and not response.errors == constants.INVALID_JSON_MESSAGE:
            raise AppException(response.errors)

    def consensus(
        self,
        project: NotEmptyStr,
        folder_names: List[int],
        image_list: Optional[List[NotEmptyStr]] = None,
        annotation_type: Optional[ANNOTATION_TYPE] = "bbox",
    ):
        """Computes consensus score for each instance of given images
            that are present in at least 2 of the given projects:

        :param project: project name
        :type project: str

        :param folder_names: list of folder names in the project for which the scores will be computed
        :type folder_names: list of str

        :param image_list: List of image names from the projects list that must be used.
                If None, then all images from the projects list will be used. Default: None
        :type image_list: list

        :param annotation_type: Type of annotation instances to consider.
                Available candidates are: ["bbox", "polygon", "point"]
        :type annotation_type: str

        :return: Pandas DateFrame with columns
                (creatorEmail, QA, imageName, instanceId, className, area, attribute, folderName, score)
        :rtype: pandas DataFrame
        """

        response = self.controller.consensus(
            project_name=project,
            folder_names=folder_names,
            image_list=image_list,
            annot_type=annotation_type,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_image_to_project(
        self,
        project: NotEmptyStr,
        img,
        image_name: Optional[NotEmptyStr] = None,
        annotation_status: Optional[str] = None,
        from_s3_bucket=None,
        image_quality_in_editor: Optional[NotEmptyStr] = None,
    ):
        """Uploads image (io.BytesIO() or filepath to image) to project.
        Sets status of the uploaded image to set_status if it is not None.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param img: image to upload
        :type img: io.BytesIO() or Path-like (str or Path)

        :param image_name: image name to set on platform. If None and img is filepath,
                           image name will be set to filename of the path
        :type image_name: str

        :param annotation_status: the annotation status of the item within the current project workflow.
                                  If None, the status will be set to the start status of the project workflow.
        :type annotation_status: str

        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str

        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
                Can be either "compressed" or "original".
                If None then the default value in project settings will be used.
        :type image_quality_in_editor: str
        """
        project_name, folder_name = extract_project_folder(project)
        if annotation_status is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “keep_status” parameter is deprecated. "
                    "Please use the “set_annotation_statuses” function instead."
                )
            )
        response = self.controller.upload_image_to_project(
            project_name=project_name,
            folder_name=folder_name,
            image_name=image_name,
            image=img,
            annotation_status=annotation_status,
            from_s3_bucket=from_s3_bucket,
            image_quality_in_editor=image_quality_in_editor,
        )
        if response.errors:
            raise AppException(response.errors)

    def upload_images_to_project(
        self,
        project: NotEmptyStr,
        img_paths: List[NotEmptyStr],
        annotation_status: str = "NotStarted",
        from_s3_bucket=None,
        image_quality_in_editor: Optional[IMAGE_QUALITY] = None,
    ):
        """Uploads all images given in list of path objects in img_paths to the project.
        Sets status of all the uploaded images to set_status if it is not None.

        If an image with existing name already exists in the project it won't be uploaded,
        and its path will be appended to the third member of return value of this
        function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param img_paths: list of Path-like (str or Path) objects to upload
        :type img_paths: list

        :param annotation_status: value to set the annotation statuses of the uploaded images
            Available statuses are::

                     * NotStarted
                     * InProgress
                     * QualityCheck
                     * Returned
                     * Completed
                     * Skipped
        :type annotation_status: str

        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str

        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
                Can be either "compressed" or "original".
                If None then the default value in project settings will be used.
        :type image_quality_in_editor: str

        :return: uploaded, could-not-upload, existing-images filepaths
        :rtype: tuple (3 members) of list of strs
        """
        project_name, folder_name = extract_project_folder(project)

        use_case = self.controller.upload_images_to_project(
            project_name=project_name,
            folder_name=folder_name,
            paths=img_paths,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
            from_s3_bucket=from_s3_bucket,
        )

        images_to_upload, existing_items = use_case.images_to_upload
        logger.info(f"Uploading {len(images_to_upload)} images to project {project}.")
        uploaded, failed_images = [], []
        if not images_to_upload:
            return uploaded, failed_images, existing_items
        if use_case.is_valid():
            with tqdm(
                total=len(images_to_upload), desc="Uploading images"
            ) as progress_bar:
                for _ in use_case.execute():
                    progress_bar.update(1)
            uploaded, failed_images, existing_items = use_case.data
            if existing_items:
                logger.info(f"Existing images {', '.join(existing_items)}")
            return uploaded, failed_images, existing_items
        raise AppException(use_case.response.errors)

    def aggregate_annotations_as_df(
        self,
        project_root: Union[NotEmptyStr, Path],
        project_type: PROJECT_TYPE,
        folder_names: Optional[List[Union[Path, NotEmptyStr]]] = None,
    ):
        """Aggregate annotations as pandas dataframe from project root.

        :param project_root: the export path of the project
        :type project_root: Path-like (str or Path)

        :param project_type: the project type, Vector/Pixel, Video or Document
        :type project_type: str

        :param folder_names: Aggregate the specified folders from project_root.
         If None aggregates all folders in the project_root
        :type folder_names: list of Pathlike (str or Path) objects

        :return: DataFrame on annotations
        :rtype: pandas DataFrame
        """
        from lib.app.analytics.aggregators import DataAggregator

        return DataAggregator(
            project_type=project_type,  # noqa
            project_root=project_root,
            folder_names=folder_names,
        ).aggregate_annotations_as_df()

    def delete_annotations(
        self, project: NotEmptyStr, item_names: Optional[List[NotEmptyStr]] = None
    ):
        """
        Delete item annotations from a given list of items.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param item_names:  item names. If None, all the annotations in the specified directory will be deleted.
        :type item_names: list of strs
        """

        project, folder = self.controller.get_project_folder_by_path(project)
        response = self.controller.annotations.delete(
            project=project, folder=folder, item_names=item_names
        )
        if response.errors:
            raise AppException(response.errors)

    def validate_annotations(
        self,
        project_type: PROJECT_TYPE,
        annotations_json: Union[NotEmptyStr, Path, dict],
    ):
        """Validates given annotation JSON.

        :param project_type: The project type Vector, Pixel, Video or Document
        :type project_type: str

        :param annotations_json: path to annotation JSON
        :type annotations_json: Path-like (str or Path)

        :return: The success of the validation
        :rtype: bool
        """
        if isinstance(annotations_json, dict):
            annotation_data = annotations_json
        else:
            with open(annotations_json, "rb") as f:
                annotation_data = json.load(f)
        response = self.controller.validate_annotations(project_type, annotation_data)
        if response.errors:
            raise AppException(response.errors)
        report = response.data
        if not report:
            return True
        print(wrap_validation_errors(report))
        return False

    def add_contributors_to_project(
        self,
        project: NotEmptyStr,
        emails: conlist(EmailStr, min_items=1),
        role: str,
    ) -> Tuple[List[str], List[str]]:
        """Add contributors to project.

        :param project: project name
        :type project: str

        :param emails: users email
        :type emails: list

        :param role: user role to apply, one of ProjectAdmin , Annotator , QA
        :type role: str

        :return: lists of added,  skipped contributors of the project
        :rtype: tuple (2 members) of lists of strs
        """
        project = self.controller.projects.get_by_name(project).data
        contributors = [
            entities.ContributorEntity(
                user_id=email,
                user_role=self.controller.service_provider.get_role_id(project, role),
            )
            for email in emails
        ]
        response = self.controller.projects.add_contributors(
            team=self.controller.get_team().data,
            project=project,
            contributors=contributors,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def invite_contributors_to_team(
        self, emails: conlist(EmailStr, min_items=1), admin: bool = False
    ) -> Tuple[List[str], List[str]]:
        """Invites contributors to the team.

        :param emails: list of contributor emails
        :type emails: list

        :param admin: enables admin privileges for the contributor
        :type admin: bool

        :return: lists of invited, skipped contributors of the team
        :rtype: tuple (2 members) of lists of strs
        """
        response = self.controller.invite_contributors_to_team(
            emails=emails, set_admin=admin
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_annotations(
        self,
        project: Union[NotEmptyStr, int],
        items: Optional[Union[List[NotEmptyStr], List[int]]] = None,
        *,
        data_spec: Literal["default", "multimodal"] = "default",
    ):
        """Returns annotations for the given list of items.

        :param project: project id or project name or folder path (e.g., “project1/folder1”).
        :type project: str or int

        :param items:  item names. If None, all the items in the specified directory will be used.
        :type items: list of strs or list of ints

        :param data_spec: Specifies the format for processing and transforming annotations before upload.

            Options are:
                    - default: Retains the annotations in their original format.
                    - multimodal: Converts annotations for multimodal projects, optimizing for
                                     compact and multimodal-specific data representation.

        :type data_spec: str, optional

        Example Usage of Multimodal Projects::

            from superannotate import SAClient


            sa = SAClient()

            # Call the get_annotations function
            response = sa.get_annotations(
                project="project1/folder1",
                items=["item_1", "item_2"],
                data_spec='multimodal'
            )

        :return: list of annotations
        :rtype: list of dict
        """
        if isinstance(project, str):
            project, folder = self.controller.get_project_folder_by_path(project)
        else:
            project = self.controller.get_project_by_id(project_id=project).data
            folder = self.controller.get_folder_by_id(
                project_id=project.id, folder_id=project.folder_id
            ).data
        response = self.controller.annotations.list(
            project,
            folder,
            items,
            transform_version="llmJsonV2" if data_spec == "multimodal" else None,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_annotations_per_frame(
        self, project: NotEmptyStr, video: NotEmptyStr, fps: int = 1
    ):
        """Returns per frame annotations for the given video.


        :param project: project name or folder path (e.g., “project1/folder1”).
        :type project: str

        :param video: video name
        :type video: str

        :param fps: how many frames per second needs to be extracted from the video.
         Will extract 1 frame per second by default.
        :type fps: str

        :return: list of annotation objects
        :rtype: list of dicts
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.get_annotations_per_frame(
            project_name, folder_name, video_name=video, fps=fps
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_priority_scores(self, project: NotEmptyStr, scores: List[PriorityScore]):
        """Upload priority scores for the given list of items.

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param scores: list of score objects
        :type scores: list of dicts

        :return: lists of uploaded, skipped items
        :rtype: tuple (2 members) of lists of strs
        """
        scores = parse_obj_as(List[PriorityScoreEntity], scores)
        project_name, folder_name = extract_project_folder(project)
        project_folder_name = project
        project, folder = self.controller.get_project_folder(
            (project_name, folder_name)
        )
        response = self.controller.projects.upload_priority_scores(
            project, folder, scores, project_folder_name
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_integrations(self):
        """Get all integrations per team

        :return: metadata objects of all integrations of the team.
        :rtype: list of dicts

        Request Example:
        ::

            client.get_integrations()


        Response Example:
        ::

            [
                {
                    "createdAt": "2023-11-27T11:16:02.000Z",
                    "id": 5072,
                    "name": "My S3 Bucket",
                    "root": "test-openseadragon-1212",
                    "type": "aws",
                    "updatedAt": "2023-12-27T11:16:02.000Z",
                    "creator_id": "example@superannotate.com"
                }
            ]
        """
        response = self.controller.integrations.list()
        if response.errors:
            raise AppException(response.errors)
        integrations = response.data
        return BaseSerializer.serialize_iterable(integrations)

    def attach_items_from_integrated_storage(
        self,
        project: NotEmptyStr,
        integration: Union[NotEmptyStr, IntegrationEntity],
        folder_path: Optional[NotEmptyStr] = None,
        *,
        query: Optional[NotEmptyStr] = None,
        item_name_column: Optional[NotEmptyStr] = None,
        custom_item_name: Optional[NotEmptyStr] = None,
        component_mapping: Optional[Dict[str, str]] = None,
    ):
        """Link images from integrated external storage to SuperAnnotate from AWS, GCP, Azure, Databricks.

        :param project: project name or folder path where items should be attached (e.g., “project1/folder1”).
        :type project: str

        :param integration: The existing integration name or metadata dict to pull items from.
            Mandatory keys in integration metadata’s dict is “name”.
        :type integration: str or dict

        :param folder_path: Points to an exact folder/directory within given storage.
            If None, items     are fetched from the root directory.
        :type folder_path: str

        :param query: (Only for Databricks). The SQL query to retrieve specific columns from Databricks.
            If provided, the function will execute the query and use the results for mapping and uploading.
        :type query: Optional[str]

        :param item_name_column: (Only for Databricks). The column name from the SQL query whose values
            will be used as item names. If this is provided, custom_item_name cannot be used.
            The column must exist in the query result.
        :type item_name_column: Optional[str]

        :param custom_item_name: (Only for Databricks). A manually defined prefix for item names.
            A random 10-character suffix will be appended to ensure uniqueness.
            If this is provided, item_name_column cannot be used.
        :type custom_item_name: Optional[str]

        :param component_mapping: (Only for Databricks). A dictionary mapping Databricks
            columns to SuperAnnotate component IDs.
        :type component_mapping: Optional[dict]


        Request Example:
        ::

            client.attach_items_from_integrated_storage(
                project="project_name",
                integration="databricks_integration",
                query="SELECT * FROM integration_data LIMIT 10",
                item_name_column="prompt",
                component_mapping={
                    "category": "_item_category",
                    "prompt_id": "id",
                    "prompt": "prompt"
                }
            )

        """
        project, folder = self.controller.get_project_folder_by_path(project)
        _integration = None
        if isinstance(integration, str):
            integration = IntegrationEntity(name=integration)
        for i in self.controller.integrations.list().data:
            if integration.name.lower() == i.name.lower():
                _integration = i
                break
        else:
            raise AppException("Integration not found.")

        response = self.controller.integrations.attach_items(
            project=project,
            folder=folder,
            integration=_integration,
            folder_path=folder_path,
            query=query,
            item_name_column=item_name_column,
            custom_item_name=custom_item_name,
            component_mapping=component_mapping,
        )
        if response.errors:
            raise AppException(response.errors)

    def query(
        self,
        project: NotEmptyStr,
        query: Optional[NotEmptyStr] = None,
        subset: Optional[NotEmptyStr] = None,
    ):
        """Return items that satisfy the given query.
        Query syntax should be in SuperAnnotate query language(https://doc.superannotate.com/docs/explore-overview).

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str

        :param query: SAQuL query string.
        :type query: str

        :param subset:  subset name. Allows you to query items in a specific subset.
            To return all the items in the specified subset, set the value of query param to None.
        :type subset: str

        :return: queried items' metadata list
        :rtype: list of dicts
        """
        project_name, folder_name = extract_project_folder(project)
        items = self.controller.query_entities(project_name, folder_name, query, subset)
        exclude = {
            "meta",
        }
        return BaseSerializer.serialize_iterable(items, exclude=exclude)

    def get_item_metadata(
        self,
        project: NotEmptyStr,
        item_name: NotEmptyStr,
        include_custom_metadata: bool = False,
    ):
        """Returns item metadata

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param item_name: item name.
        :type item_name: str

        :param include_custom_metadata: include custom metadata that has been attached to an asset.
        :type include_custom_metadata: bool

        :return: metadata of item
        :rtype: dict

        Request Example:
        ::

            client.get_item_metadata(
               project="Medical Annotations",
               item_name = "image_1.png",
               include_custom_metadata=True
            )

        Response Example:
        ::

            {
               "name": "image_1.jpeg",
               "path": "Medical Annotations/Study",
               "url": "https://sa-public-files.s3.../image_1.png",
               "annotation_status": "NotStarted",
               "annotator_email": None,
               "qa_email": None,
               "entropy_value": None,
               "createdAt": "2022-02-15T20:46:44.000Z",
               "updatedAt": "2022-02-15T20:46:44.000Z",
               "custom_metadata": {
                   "study_date": "2021-12-31",
                   "patient_id": "62078f8a756ddb2ca9fc9660",
                   "patient_sex": "female",
                   "medical_specialist": "robertboxer@ms.com",
               }
            }
        """
        project, folder = self.controller.get_project_folder_by_path(project)
        items = self.controller.items.list_items(
            project, folder, name=item_name, include=["assignments"]
        )
        item = next(iter(items), None)
        if not items:
            raise AppException("Item not found.")
        exclude = {"meta"}
        if include_custom_metadata:
            item_custom_fields = self.controller.custom_fields.list_fields(
                project=project, item_ids=[item.id]
            )
            item.custom_metadata = item_custom_fields.get(item.id)
        else:
            exclude.add("custom_metadata")

        return BaseSerializer(item).serialize(exclude=exclude)

    def search_items(
        self,
        project: NotEmptyStr,
        name_contains: NotEmptyStr = None,
        annotation_status: str = None,
        annotator_email: Optional[NotEmptyStr] = None,
        qa_email: Optional[NotEmptyStr] = None,
        recursive: bool = False,
        include_custom_metadata: bool = False,
    ):
        """Search items by filtering criteria.

        :param project: project name or folder path (e.g., “project1/folder1”).
            If recursive=False=True, then only the project name is required.
        :type project: str

        :param name_contains:  returns those items, where the given string is found anywhere within an item’s name.
            If None, all items returned, in accordance with the recursive=False parameter.
        :type name_contains: str

        :param annotation_status: returns items with the specified annotation status, which must match a predefined
            status in the project workflow. If None, all items are returned.

        :type annotation_status: str

        :param annotator_email: returns those items’ names that are assigned to the specified annotator.
            If None, all items are returned. Strict equal.
        :type annotator_email: str

        :param qa_email:  returns those items’ names that are assigned to the specified QA.
            If None, all items are returned. Strict equal.
        :type qa_email: str

        :param recursive: search in the project’s root and all of its folders.
            If False search only in the project’s root or given directory.
        :type recursive: bool

        :param include_custom_metadata: include custom metadata that has been attached to an asset.
        :type include_custom_metadata: bool

        :return: metadata of item
        :rtype: list of dicts

        Request Example:
        ::

            client.search_items(
               project="Medical Annotations",
               name_contains="image_1",
               include_custom_metadata=True
            )

        Response Example:
        ::

            [
               {
                   "name": "image_1.jpeg",
                   "path": "Medical Annotations/Study",
                   "url": "https://sa-public-files.s3.../image_1.png",
                   "annotation_status": "NotStarted",
                   "annotator_email": None,
                   "qa_email": None,
                   "entropy_value": None,
                   "createdAt": "2022-02-15T20:46:44.000Z",
                   "updatedAt": "2022-02-15T20:46:44.000Z",
                   "custom_metadata": {
                       "study_date": "2021-12-31",
                       "patient_id": "62078f8a756ddb2ca9fc9660",
                       "patient_sex": "female",
                       "medical_specialist": "robertboxer@ms.com",
                   }
               }
            ]
        """
        project, folder = self.controller.get_project_folder_by_path(project)
        query_kwargs = {"include": ["assignments"]}
        if name_contains:
            query_kwargs["name__contains"] = name_contains
        if annotation_status:
            query_kwargs["annotation_status"] = annotation_status
        if qa_email:
            query_kwargs["assignments__user_id"] = qa_email
            query_kwargs["assignments__user_role"] = "QA"
        if annotator_email:
            query_kwargs["assignments__user_id"] = annotator_email
            query_kwargs["assignments__user_role"] = "Annotator"
        if folder.is_root and recursive:
            items = []
            for folder in self.controller.folders.list(project=project).data:
                path = (
                    f"{project.name}{f'/{folder.name}' if not folder.is_root else ''}"
                )
                _items = self.controller.items.list_items(
                    project,
                    folder,
                    **query_kwargs,
                )
                for i in _items:
                    i.path = path
                items.extend(_items)
        else:
            path = f"{project.name}{f'/{folder.name}' if not folder.is_root else ''}"
            items = self.controller.items.list_items(project, folder, **query_kwargs)
            for i in items:
                i.path = path
        exclude = {"meta"}
        if include_custom_metadata:
            item_custom_fields = self.controller.custom_fields.list_fields(
                project=project, item_ids=[i.id for i in items]
            )
            for i in items:
                i.custom_metadata = item_custom_fields[i.id]
        else:
            exclude.add("custom_metadata")
        return BaseSerializer.serialize_iterable(items, exclude=exclude)

    def list_items(
        self,
        project: Union[NotEmptyStr, int],
        folder: Optional[Union[NotEmptyStr, int]] = None,
        *,
        include: List[Literal["custom_metadata", "categories"]] = None,
        **filters,
    ):
        """
        Search items by filtering criteria.

        :param project: The project name, project ID, or folder path (e.g., "project1") to search within.
                        This can refer to the root of the project or a specific subfolder.
        :type project: Union[NotEmptyStr, int]

        :param folder: The folder name or ID to search within. If None, the search will be done in the root folder of
                       the project. If both “project” and “folder” specify folders, the “project”
                       value will take priority.
        :type folder: Union[NotEmptyStr, int], optional

        :param include: Specifies additional fields to include in the response.

                Possible values are

                - "custom_metadata": Includes custom metadata attached to the item.
                - "categories": Includes categories attached to the item.
        :type include: list of str, optional

        :param filters: Specifies filtering criteria (e.g., name, ID, annotation status),
                        with all conditions combined using logical AND. Only items matching all criteria are returned.
                        If no operation is specified, an exact match is applied.


                Supported operations:
                    - __ne: Value is not equal.
                    - __in: Value is in the list.
                    - __notin: Value is not in the list.
                    - __contains: Value has the substring.
                    - __starts: Value starts with the prefix.
                    - __ends: Value ends with the suffix.

                Filter params::

                - id: int
                - id__in: list[int]
                - name: str
                - name__in:  list[str]
                - name__contains: str
                - name__starts: str
                - name__ends: str
                - annotation_status: str
                - annotation_status__in: list[str]
                - annotation_status__ne: list[str]
                - approval_status: Literal["Approved", "Disapproved", None]
                - assignments__user_id: str
                - assignments__user_id__ne: str
                - assignments__user_id__in: list[str]
                - assignments__user_role: str
                - assignments__user_id__ne: str
                - assignments__user_role__in: list[str]
                - assignments__user_role__notin: list[str]
        :type filters: ItemFilters

        :return: A list of items that match the filtering criteria.
        :rtype: list of dicts

        Request Example:
        ::

            client.list_items(
                project="Medical Annotations",
                folder="folder1",
                include=["custom_metadata"],
                annotation_status="InProgress",
                name_contains="scan"
            )

        Response Example:
        ::

            [
                {
                    "name": "scan_123.jpeg",
                    "path": "Medical Annotations/folder1",
                    "url": "https://sa-public-files.s3.../scan_123.jpeg",
                    "annotation_status": "InProgress",
                    "createdAt": "2022-02-10T14:32:21.000Z",
                    "updatedAt": "2022-02-15T20:46:44.000Z",
                    "custom_metadata": {
                        "study_date": "2021-12-31",
                        "patient_id": "62078f8a756ddb2ca9fc9660",
                        "medical_specialist": "robertboxer@ms.com"
                    }
                }
            ]

        Request Example with include categories:
        ::

            client.list_items(
                project="My Multimodal",
                folder="folder1",
                include=["categories"]
            )

        Response Example:
        ::

            [
                {
                    "id": 48909383,
                    "name": "scan_123.jpeg",
                    "path": "Medical Annotations/folder1",
                    "url": "https://sa-public-files.s3.../scan_123.jpeg",
                    "annotation_status": "InProgress",
                    "createdAt": "2022-02-10T14:32:21.000Z",
                    "updatedAt": "2022-02-15T20:46:44.000Z",
                    "entropy_value": None,
                    "assignments": [],
                    "categories": [
                        {
                            "createdAt": "2025-01-29T13:51:39.000Z",
                            "updatedAt": "2025-01-29T13:51:39.000Z",
                            "id": 328577,
                            "name": "my_category",
                        },
                    ],
                }
            ]

        Additional Filter Examples:
        ::

            client.list_items(
                project="Medical Annotations",
                folder="folder2",
                annotation_status="Completed",
                name__in=["1.jpg", "2.jpg", "3.jpg"]
            )

            # Filter items assigned to a specific QA
            client.list_items(
                project="Medical Annotations",
                assignee__user_id="qa@example.com"
            )
        """
        project = (
            self.controller.get_project_by_id(project).data
            if isinstance(project, int)
            else self.controller.get_project(project)
        )
        if (
            include
            and "categories" in include
            and project.type != ProjectType.MULTIMODAL.value
        ):
            raise AppException(
                "The 'categories' option in the 'include' field is only supported for Multimodal projects."
            )
        if folder is None:
            folder = self.controller.get_folder(project, "root")
        else:
            if isinstance(folder, int):
                folder = self.controller.get_folder_by_id(
                    project_id=project.id, folder_id=folder
                ).data
            else:
                folder = self.controller.get_folder(project, folder)
        _include = {"assignments"}
        if include:
            _include.update(set(include))
        include = list(_include)
        include_custom_metadata = "custom_metadata" in include
        if include_custom_metadata:
            include.remove("custom_metadata")
        res = self.controller.items.list_items(
            project, folder, include=include, **filters
        )
        if include_custom_metadata:
            item_custom_fields = self.controller.custom_fields.list_fields(
                project=project, item_ids=[i.id for i in res]
            )
            for i in res:
                i.custom_metadata = item_custom_fields[i.id]
        exclude = {"meta", "annotator_email", "qa_email"}
        if not include_custom_metadata:
            exclude.add("custom_metadata")
        return BaseSerializer.serialize_iterable(res, exclude=exclude, by_alias=False)

    def list_projects(
        self,
        *,
        include: List[Literal["custom_fields"]] = None,
        **filters,
    ):
        """
        Search projects by filtering criteria.

        :param include: Specifies additional fields to include in the response.

            Possible values are

            - "custom_fields": Includes the custom fields assigned to each project.
        :type include: list of str, optional

        :param filters: Specifies filtering criteria, with all conditions combined using logical AND.

            - Only users matching all filter conditions are returned.

            - If no filter operation is provided, an exact match is applied.

            Supported operations:

            - __in: Value is in the provided list.
            - __notin: Value is not in the provided list.
            - __ne: Value is not equal to the given value.
            - __contains: Value contains the specified substring.
            - __starts: Value starts with the given prefix.
            - __ends: Value ends with the given suffix.
            - __gt: Value is greater than the given number.
            - __gte: Value is greater than or equal to the given number.
            - __lt: Value is less than the given number.
            - __lte: Value is less than or equal to the given number.

            Filter params::

            - id: int
            - id__in: list[int]
            - name: str
            - name__in:  list[str]
            - name__contains: str
            - name__starts: str
            - name__ends: str
            - status: Literal[“NotStarted”, “InProgress”, “Completed”, “OnHold”]
            - status__ne: Literal[“NotStarted”, “InProgress”, “Completed”, “OnHold”]
            - status__in: List[Literal[“NotStarted”, “InProgress”, “Completed”, “OnHold”]]
            - status__notin: List[Literal[“NotStarted”, “InProgress”, “Completed”, “OnHold”]]

            Custom Fields Filtering:

                - Custom fields must be prefixed with `custom_field__`.
                - Example: custom_field__Due_date__gte="1738281600" (filtering users whose Due_date is after the given Unix timestamp).
                - If include does not include “custom_fields” but filter contains ‘custom_field’, an error will be returned

            - **Text** custom field only works with the following filter params: __in, __notin, __contains
            - **Numeric** custom field only works with the following filter params: __in, __notin, __ne, __gt, __gte, __lt, __lte
            - **Single-select** custom field only works with the following filter params: __in, __notin, __contains
            - **Multi-select** custom field only works with the following filter params: __in, __notin
            - **Date picker** custom field only works with the following filter params: __gt, __gte, __lt, __lte

            **If custom field has a space, please use the following format to filter them**:
            ::

                project_filters = {
                    "custom_field__new single select custom field__contains": "text"
                }
                client.list_projects(include=["custom_fields"], **project_filters)

        :type filters: ProjectFilters, optional

        :return: A list of project metadata that matches the filtering criteria.
        :rtype: list of dicts

        Request Example:
        ::

            client.list_projects(
                include=["custom_fields"],
                status__in=["InProgress", "Completed"],
                name__contains="Medical",
                custom_field__Tag__in=["Tag1", "Tag3"]
            )

        Response Example:
        ::

            [
                {
                    "classes": [],
                    "completed_items_count": None,
                    "contributors": [],
                    "createdAt": "2025-02-04T12:04:01+00:00",
                    "creator_id": "ecample@email.com",
                    "custom_fields": {
                        "Notes": "Something",
                        "Ann Quality threshold": 80,
                        "Tag": ["Tag1","Tag2","Tag3"],
                        "Due date": 1738281600.0,
                        "Other_Custom_Field": None,
                    },
                    "description": "DESCRIPTION",
                    "entropy_status": 1,
                    "folder_id": 1191383,
                    "id": 902174,
                    "instructions_link": None,
                    "item_count": None,
                    "name": "Medical Annotations",
                    "root_folder_completed_items_count": None,
                    "settings": [],
                    "sharing_status": None,
                    "status": "InProgress",
                    "team_id": 233435,
                    "type": "Vector",
                    "updatedAt": "2024-02-04T12:04:01+00:00",
                    "upload_state": "INITIAL",
                    "users": [],
                    "workflow_id": 1,
                }
            ]
        """
        return [
            WMProjectSerializer(p).serialize()
            for p in self.controller.projects.list_projects(include=include, **filters)
        ]

    def attach_items(
        self,
        project: Union[NotEmptyStr, dict],
        attachments: Union[NotEmptyStr, Path, conlist(Attachment, min_items=1)],
        annotation_status: str = None,
    ):
        """
        Link items from external storage to SuperAnnotate using URLs.

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param attachments: path to CSV file or list of dicts containing attachments URLs.
        :type attachments: path-like (str or Path) or list of dicts
        :param annotation_status: the annotation status of the item within the current project workflow.
                                  If None, the status will be set to the start status of the project workflow.

        :type annotation_status: str

        :return: uploaded, failed and duplicated item names
        :rtype: tuple of list of strs

        Example:
        ::

            client = SAClient()
            client.attach_items(
                project="Medical Annotations",
                attachments=[{"name": "item", "url": "https://..."}]
             )

        Example of attaching items from custom integration:
        ::

            client = SAClient()
            client.attach_items(
                project="Medical Annotations",
                attachments=[
                    {
                        "name": "item",
                        "url": "https://bucket-name.s3…/example.png"
                        "integration": "custom-integration-name"
                        }
                    ]
            )
        """
        if annotation_status is not None:
            warnings.warn(
                DeprecationWarning(
                    "The “keep_status” parameter is deprecated. "
                    "Please use the “set_annotation_statuses” function instead."
                )
            )
        project_name, folder_name = extract_project_folder(project)
        try:
            attachments = parse_obj_as(List[AttachmentEntity], attachments)
            unique_attachments = set(attachments)
            duplicate_attachments = [
                item
                for item, count in collections.Counter(attachments).items()
                if count > 1
            ]
        except ValidationError:
            (
                unique_attachments,
                duplicate_attachments,
            ) = get_name_url_duplicated_from_csv(attachments)
        if duplicate_attachments:
            logger.info("Dropping duplicates.")
        unique_attachments = parse_obj_as(List[AttachmentEntity], unique_attachments)
        uploaded, fails, duplicated = [], [], []
        _unique_attachments = []
        if any(i.integration for i in unique_attachments):
            integtation_item_map = {
                i.name: i
                for i in self.controller.integrations.list().data
                if i.type == IntegrationTypeEnum.CUSTOM
            }
            invalid_integrations = set()
            for attachment in unique_attachments:
                if attachment.integration:
                    if attachment.integration in integtation_item_map:
                        attachment.integration_id = integtation_item_map[
                            attachment.integration
                        ].id
                    else:
                        invalid_integrations.add(attachment.integration)
                        continue
                _unique_attachments.append(attachment)
            if invalid_integrations:
                logger.error(
                    f"The ['{','.join(invalid_integrations)}'] integrations specified for the items doesn't exist in the "
                    "list of integrations on the platform. Any associated items will be skipped."
                )
        else:
            _unique_attachments = unique_attachments

        if _unique_attachments:
            logger.info(
                f"Attaching {len(_unique_attachments)} file(s) to project {project}."
            )
            project, folder = self.controller.get_project_folder(
                (project_name, folder_name)
            )
            response = self.controller.items.attach(
                project=project,
                folder=folder,
                attachments=_unique_attachments,
                annotation_status=annotation_status,
            )
            if response.errors:
                raise AppException(response.errors)
            uploaded, duplicated = response.data
            fails = [
                attachment.name
                for attachment in _unique_attachments
                if attachment.name not in uploaded and attachment.name not in duplicated
            ]
        return uploaded, fails, duplicated

    def generate_items(
        self,
        project: Union[NotEmptyStr, Tuple[int, int], Tuple[str, str]],
        count: int,
        name: str,
    ):
        """
        Generate multiple items in a specific project and folder.
        If there are no items in the folder, it will generate a blank item otherwise, it will generate items based on the Custom Form.

        :param project: Project and folder as a tuple, folder is optional.
        :type project: Union[str, Tuple[int, int], Tuple[str, str]]

        :param count: the count of items to generate
        :type count: int

        :param name: the name of the item. After generating the items,
                     the item names will contain the provided name and a numeric suffix based on the item count.
        :type name: str
        """
        project, folder = self.controller.get_project_folder(project)

        response = self.controller.items.generate_items(
            project=project, folder=folder, count=count, name=name
        )
        if response.errors:
            raise AppException(response.errors)
        logger.info(f"{response.data} items successfully generated.")

    def copy_items(
        self,
        source: Union[NotEmptyStr, dict],
        destination: Union[NotEmptyStr, dict],
        items: Optional[List[NotEmptyStr]] = None,
        include_annotations: bool = True,
        duplicate_strategy: Literal[
            "skip", "replace", "replace_annotations_only"
        ] = "skip",
    ):
        """Copy items in bulk between folders in a project

        :param source: project name (root) or folder path to pick items from (e.g., “project1/folder1”).
        :type source: str

        :param destination: project name (root) or folder path to place copied items (e.g., “project1/folder2”).
        :type destination: str

        :param items: names of items to copy. If None, all items from the source directory will be copied.
        :type items: list of str

        :param include_annotations: enables the copying of item data, including annotations, status, priority score,
         approval state, and category. If set to False, only the items will be copied without additional data.
        :type include_annotations: bool

        :param duplicate_strategy: Specifies the strategy for handling duplicate items in the destination.
         The default value is "skip".

            - "skip": skips duplicate items in the destination and continues with the next item.
            - "replace": replaces the annotations, status, priority score, approval state, and category of duplicate items.
            - "replace_annotations_only": replaces only the annotations of duplicate items,
              leaving other data (status, priority score, approval state, and category) unchanged.

        :type duplicate_strategy: Literal["skip", "replace", "replace_annotations_only"]

        :return: list of skipped item names
        :rtype: list of strs
        """

        if not include_annotations and duplicate_strategy != "skip":
            duplicate_strategy = "skip"
            logger.warning(
                "Copy operation continuing without annotations and metadata due to include_annotations=False."
            )

        project_name, source_folder = extract_project_folder(source)
        to_project_name, destination_folder = extract_project_folder(destination)
        if project_name != to_project_name:
            raise AppException("Source and destination projects should be the same")
        project = self.controller.get_project(project_name)
        from_folder = self.controller.get_folder(project, source_folder)
        to_folder = self.controller.get_folder(project, destination_folder)
        response = self.controller.items.copy_multiple(
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            item_names=items,
            include_annotations=include_annotations,
            duplicate_strategy=duplicate_strategy,
        )
        if response.errors:
            raise AppException(response.errors)

        return response.data

    def move_items(
        self,
        source: Union[NotEmptyStr, dict],
        destination: Union[NotEmptyStr, dict],
        items: Optional[List[NotEmptyStr]] = None,
        duplicate_strategy: Literal[
            "skip", "replace", "replace_annotations_only"
        ] = "skip",
    ):
        """Move items in bulk between folders in a project

        :param source: project name (root) or folder path to pick items from (e.g., “project1/folder1”).
        :type source: str

        :param destination: project name (root) or folder path to move items to (e.g., “project1/folder2”).
        :type destination: str

        :param items: names of items to move. If None, all items from the source directory will be moved.
        :type items: list of str

        :param duplicate_strategy: Specifies the strategy for handling duplicate items in the destination.
         The default value is "skip".

            - "skip": skips duplicate items in the destination and continues with the next item.
            - "replace": replaces the annotations, status, priority score, approval state, and category of duplicate items.
            - "replace_annotations_only": replaces only the annotations of duplicate items,
              leaving other data (status, priority score, approval state, and category) unchanged.

        :type duplicate_strategy: Literal["skip", "replace", "replace_annotations_only"]

        :return: list of skipped item names
        :rtype: list of strs
        """

        project_name, source_folder = extract_project_folder(source)
        to_project_name, destination_folder = extract_project_folder(destination)
        if project_name != to_project_name:
            raise AppException("Source and destination projects should be the same")

        project = self.controller.get_project(project_name)
        source_folder = self.controller.get_folder(project, source_folder)
        destination_folder = self.controller.get_folder(project, destination_folder)
        response = self.controller.items.move_multiple(
            project=project,
            from_folder=source_folder,
            to_folder=destination_folder,
            item_names=items,
            duplicate_strategy=duplicate_strategy,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def set_annotation_statuses(
        self,
        project: Union[NotEmptyStr, dict],
        annotation_status: NotEmptyStr,
        items: Optional[List[NotEmptyStr]] = None,
    ):
        """Sets annotation statuses of items.

        :param project: project name or folder path (e.g., “project1/folder1”).
        :type project: str

        :param annotation_status: The desired status to set for the annotation.
            This status should match one of the predefined statuses available in the project workflow.
        :type annotation_status: str

        :param items:  item names. If None, all the items in the specified directory will be used.
        :type items: list of strs
        """

        project, folder = self.controller.get_project_folder_by_path(project)
        response = self.controller.items.set_annotation_statuses(
            project=project,
            folder=folder,
            annotation_status=annotation_status,
            item_names=items,
        )
        if response.errors:
            raise AppException(response.errors)
        logger.info("Annotation statuses of items changed")

    def download_annotations(
        self,
        project: Union[NotEmptyStr, dict],
        path: Union[str, Path] = None,
        items: Optional[List[NotEmptyStr]] = None,
        recursive: bool = False,
        callback: Callable = None,
        data_spec: Literal["default", "multimodal"] = "default",
    ):
        """Downloads annotation JSON files of the selected items to the local directory.

        :param project: project name or folder path (e.g., “project1/folder1”).
        :type project: str

        :param path:  local directory path where the annotations will be downloaded.
                If none, the current directory is used.
        :type path: Path-like (str or Path)

        :param items: list of item names whose annotations will be downloaded
                (e.g., ["Image_1.jpeg", "Image_2.jpeg"]). If the value is None,
                then all the annotations of the given directory will be downloaded.

        :type items: list of str

        :param recursive: download annotations from the project’s root
                and all of its folders with the preserved structure.
                If False download only from the project’s root or given directory.
        :type recursive: bool

        :param callback: a function that allows you to modify each annotation’s dict before downloading.
         The function receives each annotation as an argument and the returned value will be applied to the download.
        :type callback: callable

        :param data_spec: Specifies the format for processing and transforming annotations before upload.

            Options are:
                    - default: Retains the annotations in their original format.
                    - multimodal: Converts annotations for multimodal projects, optimizing for
                                     compact and multimodal-specific data representation.

        :type data_spec: str, optional

        Example Usage of Multimodal Projects::

            from superannotate import SAClient


            sa = SAClient()

            # Call the get_annotations function
            response = sa.download_annotations(
                project="project1/folder1",
                path="path/to/download",
                items=["item_1", "item_2"],
                data_spec='multimodal'
            )


        :return: local path of the downloaded annotations folder.
        :rtype: str
        """
        project_name, folder_name = extract_project_folder(project)
        project, folder = self.controller.get_project_folder(
            (project_name, folder_name)
        )
        response = self.controller.annotations.download(
            project=project,
            folder=folder,
            destination=path,
            recursive=recursive,
            item_names=items,
            callback=callback,
            transform_version="llmJsonV2" if data_spec == "multimodal" else None,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_subsets(self, project: Union[NotEmptyStr, dict]):
        """Get Subsets

        :param project: project name (e.g., “project1”)
        :type project: str

        :return: subsets’ metadata
        :rtype: list of dicts
        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.projects.get_by_name(project_name).data
        response = self.controller.subsets.list(project)
        if response.errors:
            raise AppException(response.errors)
        return BaseSerializer.serialize_iterable(response.data, ["name"])

    def create_custom_fields(self, project: NotEmptyStr, fields: dict):
        """Create custom fields for items in a project in addition to built-in metadata.
        Using this function again with a different schema won't override the existing fields, but add new ones.
        Use the upload_custom_values() function to fill them with values for each item.

        :param project: project name  (e.g., “project1”)
        :type project: str

        :param fields:  dictionary describing the fields and their specifications added to the project.
         You can see the schema structure <here>.
        :type fields: dict

        :return: custom fields actual schema of the project
        :rtype: dict

        Supported Types:

        ==============  ======================
                    number
        --------------------------------------
         field spec           spec value
        ==============  ======================
        minimum         any number (int or float)
        maximum         any number (int or float)
        enum            list of numbers (int or float)
        ==============  ======================

        ==============  ======================
                    string
        --------------------------------------
         field spec           spec value
        ==============  ======================
        format          “email” (user@example.com) or “date” (YYYY-MM-DD)

        enum            list of strings
        ==============  ======================

        ::

            custom_fields = {
               "study_date": {
                   "type": "string",
                   "format": "date"
               },
               "patient_id": {
                   "type": "string"
               },
               "patient_sex": {
                   "type": "string",
                   "enum": [
                       "male", "female"
                   ]
               },
               "patient_age": {
                   "type": "number"
               },
               "medical_specialist": {
                   "type": "string",
                   "format": "email"
               },
               "duration": {
                   "type": "number",
                   "minimum": 10
               }
            }

            client = SAClient()
            client.create_custom_fields(
               project="Medical Annotations",
               fields=custom_fields
            )

        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.projects.get_by_name(project_name).data
        response = self.controller.custom_fields.create_schema(
            project=project, schema=fields
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_custom_fields(self, project: NotEmptyStr):
        """Get the schema of the custom fields defined for the project

        :param project: project name  (e.g., “project1”)
        :type project: str

        :return: custom fields actual schema of the project
        :rtype: dict

        Response Example:
        ::

            {
               "study_date": {
                   "type": "string",
                   "format": "date"
               },
               "patient_id": {
                   "type": "string"
               },
               "patient_sex": {
                   "type": "string",
                   "enum": [
                       "male", "female"
                   ]
               },
               "patient_age": {
                   "type": "number"
               },
               "medical_specialist": {
                   "type": "string",
                   "format": "email"
               },
               "duration": {
                   "type": "number",
                   "minimum": 10
               }
            }
        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.projects.get_by_name(project_name).data
        response = self.controller.custom_fields.get_schema(project=project)
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def delete_custom_fields(
        self, project: NotEmptyStr, fields: conlist(str, min_items=1)
    ):
        """Remove custom fields from a project’s custom metadata schema.

        :param project: project name  (e.g., “project1”)
        :type project: str

        :param fields: list of field names to remove
        :type fields: list of strs

        :return: custom fields actual schema of the project
        :rtype: dict

        Request Example:
        ::

            client = SAClient()
            client.delete_custom_fields(
               project = "Medical Annotations",
               fields = ["duration", patient_age]
            )

        Response Example:
        ::

            {
                "study_date": {
                   "type": "string",
                   "format": "date"
                },
                "patient_id": {
                   "type": "string"
                },
                "patient_sex": {
                   "type": "string",
                   "enum": [
                       "male", "female"
                   ]
                },
                "medical_specialist": {
                   "type": "string",
                   "format": "email"
                }
            }

        """
        project_name, _ = extract_project_folder(project)
        project = self.controller.projects.get_by_name(project_name).data
        response = self.controller.custom_fields.delete_schema(
            project=project, fields=fields
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_custom_values(
        self, project: NotEmptyStr, items: conlist(Dict[str, dict], min_items=1)
    ):
        """
        Attach custom metadata to items.
        SAClient.get_item_metadata(), SAClient.search_items(), SAClient.query() methods
        will return the item metadata and custom metadata.

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param items:  list of name-data pairs.
            The key of each dict indicates an existing item name and the value represents the custom metadata dict.
            The values for the corresponding keys will be added to an item or will be overridden.
        :type items: list of dicts

        :return: dictionary with succeeded and failed item names.
        :rtype: dict

        Request Example:
        ::

            client = SAClient()

            items_values = [
               {
                   "image_1.png": {
                       "study_date": "2021-12-31",
                       "patient_id": "62078f8a756ddb2ca9fc9660",
                       "patient_sex": "female",
                       "medical_specialist": "robertboxer@ms.com"
                   }
               },
               {
                   "image_2.png": {
                       "study_date": "2021-12-31",
                       "patient_id": "62078f8a756ddb2ca9fc9661",
                       "patient_sex": "female",
                       "medical_specialist": "robertboxer@ms.com"
                   }
               },
               {
                   "image_3.png": {
                       "study_date": "2011-10-05T14:48:00.000Z",
                       "patient_": "62078f8a756ddb2ca9fc9660",
                       "patient_sex": "female",
                       "medical_specialist": "robertboxer"
                   }
               }
            ]

            client.upload_custom_values(
               project = "Medical Annotations",
               items = items_values
            )

        Response Example:
        ::

            {
               "successful_items_count": 2,
               "failed_items_names": ["image_3.png"]
            }
        """

        project_name, folder_name = extract_project_folder(project)
        project, folder = self.controller.get_project_folder(
            (project_name, folder_name)
        )
        response = self.controller.custom_fields.upload_values(
            project=project, folder=folder, items=items
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def delete_custom_values(
        self, project: NotEmptyStr, items: conlist(Dict[str, List[str]], min_items=1)
    ):
        """
        Remove custom data from items

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param items:   list of name-custom data dicts.
            The key of each dict element indicates an existing item in the project root or folder.
            The value should be the list of fields to be removed from the given item.
            Please note, that the function removes pointed metadata from a given item.
            To delete metadata for all items you should delete it from the custom metadata schema.
            To override values for existing fields, use SAClient.upload_custom_values()
        :type items: list of dicts

        Request Example:
        ::

            client.delete_custom_values(
                project = "Medical Annotations",
                items = [
                   {"image_1.png": ["study_date", "patient_sex"]},
                   {"image_2.png": ["study_date", "patient_sex"]}
                ]
            )
        """
        project_name, folder_name = extract_project_folder(project)
        project, folder = self.controller.get_project_folder(
            (project_name, folder_name)
        )
        response = self.controller.custom_fields.delete_values(
            project=project, folder=folder, items=items
        )
        if response.errors:
            raise AppException(response.errors)

    def add_items_to_subset(
        self, project: NotEmptyStr, subset: NotEmptyStr, items: List[dict]
    ):
        """

        Associates selected items with a given subset. Non-existing subset will be automatically created.

        :param project:  project name (e.g., “project1”)
        :type project: str

        :param subset: a name of an existing/new subset to associate items with.
                New subsets will be automatically created.
        :type subset: str

        :param items: list of items metadata.
                Required keys are 'name' and 'path' if the 'id' key is not provided in the dict.
        :type items: list of dicts

        :return: dictionary with succeeded, skipped and failed items lists.
        :rtype: dict

        Request Example:
        ::

            client = SAClient()

            # option 1
            queried_items = client.query(
                project="Image Project",
                query="instance(error = true)"
             )

            client.add_items_to_subset(
                project="Medical Annotations",
                subset="Brain Study - Disapproved",
                items=queried_items
            )
            # option 2
            items_list = [
                {
                    'name': 'image_1.jpeg',
                    'path': 'Image Project'
                },
                {
                    'name': 'image_2.jpeg',
                    'path': 'Image Project/Subfolder A'
                }
            ]

            client.add_items_to_subset(
                project="Image Project",
                subset="Subset Name",
                items=items_list

            )

        Response Example:
        ::

            {
                "succeeded": [
                    {
                        'name': 'image_1.jpeg',
                        'path': 'Image Project'
                    },
                    {
                        'name': 'image_2.jpeg',
                        'path': 'Image Project/Subfolder A'
                    }
                ],
                "failed": [],
                "skipped": []
            }
        """

        project_name, _ = extract_project_folder(project)
        project = self.controller.projects.get_by_name(project_name).data
        response = self.controller.subsets.add_items(project, subset, items)
        if response.errors:
            raise AppException(response.errors)

        return response.data

    def set_approval_statuses(
        self,
        project: NotEmptyStr,
        approval_status: Optional[APPROVAL_STATUS],
        items: Optional[List[NotEmptyStr]] = None,
    ):
        """Sets annotation statuses of items

        :param project: project name or folder path (e.g., “project1/folder1”).
        :type project: str

        :param approval_status: approval status to set. \n
            Available statuses are::

                     * None
                     * Approved
                     * Disapproved
        :type approval_status: str

        :param items:  item names to set the mentioned status for. If None, all the items in the project will be used.
        :type items: list of strs
        """
        project, folder = self.controller.get_project_folder_by_path(project)
        response = self.controller.items.set_approval_statuses(
            project=project,
            folder=folder,
            approval_status=approval_status,
            item_names=items,
        )
        if response.errors:
            raise AppException(response.errors)

    def item_context(
        self,
        path: Union[str, Tuple[NotEmptyStr, NotEmptyStr], Tuple[int, int]],
        item: Union[NotEmptyStr, int],
        overwrite: bool = True,
    ) -> ItemContext:
        """
        Creates an “ItemContext” for managing item annotations and metadata.

        This function allows you to manage annotations and metadata for an item located within a
        specified project and folder. The path to the item can be provided either as a string or a tuple,
        and you can specify the item using its name or ID.
        It returns an “ItemContext” that automatically saves any changes to annotations when the context is exited.

        :param path: Specifies the project and folder containing the item. Can be one of:
            - A string path, e.g., "project_name/folder_name".
            - A tuple of strings, e.g., ("project_name", "folder_name").
            - A tuple of integers (IDs), e.g., (project_id, folder_id).
        :type path: Union[str, Tuple[str, str], Tuple[int, int]]

        :param item: The name or ID of the item for which the context is being created.
        :type item: Union[str, int]

        :param overwrite: If `True`, annotations are overwritten during saving. Defaults is `True`.
            If `False`, raises a `FileChangedError` if the item was modified concurrently.
        :type overwrite: bool

        :raises AppException: If the provided `path` is invalid or if the item cannot be located.

        :return: An `ItemContext` object to manage the specified item's annotations and metadata.
        :rtype: ItemContext

        .. seealso::
            For more details, see :class:`ItemContext` nested class.

        **Examples:**

        Create an `ItemContext` using a string path and item name:

        .. code-block:: python

            with client.item_context("project_name/folder_name", "item_name") as item_context:
                metadata = item_context.get_metadata()
                value = item_context.get_component_value("prompts")
                item_context.set_component_value("prompts", value)

        Create an `ItemContext` using a tuple of strings and an item ID:

        .. code-block:: python

            with client.item_context(("project_name", "folder_name"), 12345) as context:
                metadata = context.get_metadata()
                print(metadata)

        Create an `ItemContext` using a tuple of IDs and an item name:

        .. code-block:: python

            with client.item_context((101, 202), "item_name") as context:
                value = context.get_component_value("component_id")
                print(value)

        Save annotations automatically after modifying component values:

        .. code-block:: python

            with client.item_context("project_name/folder_name", "item_name", overwrite=True) as context:
                context.set_component_value("component_id", "new_value")
            # No need to call .save(), changes are saved automatically on context exit.

        Handle exceptions during context execution:

        .. code-block:: python

            from superannotate import FileChangedError

            try:
                with client.item_context((101, 202), "item_name") as context:
                    context.set_component_value("component_id", "new_value")
            except FileChangedError as e:
                print(f"An error occurred: {e}")
        """
        if isinstance(path, str):
            project, folder = self.controller.get_project_folder_by_path(path)
        elif len(path) == 2 and all([isinstance(i, str) for i in path]):
            project = self.controller.get_project(path[0])
            folder = self.controller.get_folder(project, path[1])
        elif len(path) == 2 and all([isinstance(i, int) for i in path]):
            project = self.controller.get_project_by_id(path[0]).data
            folder = self.controller.get_folder_by_id(path[1], project.id).data
        else:
            raise AppException("Invalid path provided.")
        if project.type != ProjectType.MULTIMODAL:
            raise AppException(
                "This function is only supported for Multimodal projects."
            )
        if isinstance(item, int):
            _item = self.controller.get_item_by_id(item_id=item, project=project)
        else:
            items = self.controller.items.list_items(project, folder, name=item)
            if not items:
                raise AppException("Item not found.")
            _item = items[0]
        if project.type != ProjectType.MULTIMODAL:
            raise AppException(
                f"The function is not supported for {project.type.name} projects."
            )
        return ItemContext(
            controller=self.controller,
            project=project,
            folder=folder,
            item=_item,
            overwrite=overwrite,
        )

    def list_workflows(self):
        """
        Lists team’s all workflows and their metadata

        :return: metadata of workflows
        :rtype: list of dicts


        Request Example:
        ::

            client.list_workflows()


        Response Example:
        ::

            [
                {
                    "createdAt": "2024-09-03T12:48:09+00:00",
                    "updatedAt": "2024-09-04T12:48:09+00:00",
                    "id": 1,
                    "name": "System workflow",
                    "type": "system",
                    "description": "This workflow is generated by the system, and prevents annotators from completing items.",
                    "raw_config": {"roles": ["Annotator", "QA"], ...}
                },
                {
                    "createdAt": "2025-01-03T12:48:09+00:00",
                    "updatedAt": "2025-01-05T12:48:09+00:00",
                    "id": 58758,
                    "name": "Custom workflow",
                    "type": "user",
                    "description": "This workflow custom build.",
                    "raw_config": {"roles": ["Custom Annotator", "Custom QA"], ...}
                }
            ]
        """
        workflows = self.controller.service_provider.work_management.list_workflows(
            EmptyQuery()
        )
        return BaseSerializer.serialize_iterable(workflows.data)
