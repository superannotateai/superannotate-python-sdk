import copy
import io
import logging
import os
from abc import ABCMeta
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple
from typing import Union

import lib.core as constances
from lib.core import ApprovalStatus
from lib.core import usecases
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AttachmentEntity
from lib.core.entities import BaseItemEntity
from lib.core.entities import ConfigEntity
from lib.core.entities import ContributorEntity
from lib.core.entities import CustomFieldEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import PROJECT_ITEM_ENTITY_MAP
from lib.core.entities import ProjectEntity
from lib.core.entities import SettingEntity
from lib.core.entities import TeamEntity
from lib.core.entities import UserEntity
from lib.core.entities.classes import AnnotationClassEntity
from lib.core.entities.filters import ItemFilters
from lib.core.entities.filters import ProjectFilters
from lib.core.entities.filters import UserFilters
from lib.core.entities.integrations import IntegrationEntity
from lib.core.entities.work_managament import ScoreEntity
from lib.core.entities.work_managament import ScorePayloadEntity
from lib.core.enums import CustomFieldEntityEnum
from lib.core.enums import CustomFieldType
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.exceptions import FileChangedError
from lib.core.jsx_conditions import EmptyQuery
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import Join
from lib.core.jsx_conditions import OperatorEnum
from lib.core.jsx_conditions import Query
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.service_types import PROJECT_TYPE_RESPONSE_MAP
from lib.core.usecases import serialize_item_entity
from lib.infrastructure.custom_entities import generate_schema
from lib.infrastructure.helpers import timed_lru_cache
from lib.infrastructure.query_builder import FieldValidationHandler
from lib.infrastructure.query_builder import IncludeHandler
from lib.infrastructure.query_builder import ItemFilterHandler
from lib.infrastructure.query_builder import ProjectFilterHandler
from lib.infrastructure.query_builder import QueryBuilderChain
from lib.infrastructure.query_builder import UserFilterHandler
from lib.infrastructure.repositories import S3Repository
from lib.infrastructure.serviceprovider import ServiceProvider
from lib.infrastructure.services.http_client import HttpClient
from lib.infrastructure.utils import divide_to_chunks
from lib.infrastructure.utils import extract_project_folder
from typing_extensions import Unpack


def build_condition(**kwargs) -> Condition:
    condition = Condition.get_empty_condition()
    if any(kwargs.values()):
        for key, value in ((key, value) for key, value in kwargs.items() if value):
            condition = condition & Condition(key, value, EQ)
    return condition


def serialize_custom_fields(
    team_id: int,
    project_id: Optional[int],
    service_provider: ServiceProvider,
    data: List[dict],
    entity: CustomFieldEntityEnum,
    parent_entity: CustomFieldEntityEnum,
) -> List[dict]:
    context = {"team_id": team_id, "project_id": project_id}

    existing_custom_fields = service_provider.list_custom_field_names(
        context, entity, parent=parent_entity
    )
    for i in range(len(data)):
        if not data[i]:
            data[i] = {}
        updated_fields = {}

        for custom_field_name, field_value in data[i].items():
            field_id = int(custom_field_name)
            try:
                component_id = service_provider.get_custom_field_component_id(
                    context, field_id, entity=entity, parent=parent_entity
                )
            except AppException:
                # The component template can be deleted, but not from the entity, so it will be skipped.
                continue

            if field_value and component_id == CustomFieldType.DATE_PICKER.value:
                field_value /= 1000  # Convert timestamp

            new_field_name = service_provider.get_custom_field_name(
                context, field_id, entity=entity, parent=parent_entity
            )
            updated_fields[new_field_name] = field_value

        data[i].clear()
        data[i].update(updated_fields)

        for existing_custom_field in existing_custom_fields:
            if existing_custom_field not in data[i]:
                data[i][existing_custom_field] = None

    return data


class BaseManager:
    def __init__(self, service_provider: ServiceProvider):
        self.service_provider = service_provider


class WorkManagementManager(BaseManager):
    def list_score_templates(self):
        return self.service_provider.work_management.list_scores()

    def get_user_metadata(
        self, pk: Union[str, int], include: List[Literal["custom_fields"]] = None
    ):
        if isinstance(pk, int):
            filters = {"id": pk}
        else:
            filters = {"email": pk}
        users = self.list_users(include=include, **filters)
        if not users:
            raise AppException("User not found.")
        return users[0]

    def set_custom_field_value(
        self,
        entity_id: int,
        entity: CustomFieldEntity,
        parent_entity: CustomFieldEntityEnum,
        field_name: str,
        value: Any,
    ):
        _context = {"team_id": self.service_provider.client.team_id}
        if entity == CustomFieldEntityEnum.PROJECT:
            _context["project_id"] = entity_id

        template_id = self.service_provider.get_custom_field_id(
            _context, field_name, entity=entity, parent=parent_entity
        )
        component_id = self.service_provider.get_custom_field_component_id(
            _context, template_id, entity=entity, parent=parent_entity
        )
        # timestamp: convert seconds to milliseconds
        if component_id == CustomFieldType.DATE_PICKER.value and value is not None:
            try:
                value = value * 1000
            except Exception:
                raise AppException("Invalid custom field value provided.")
        self.service_provider.work_management.set_custom_field_value(
            entity_id=entity_id,
            entity=entity,
            parent_entity=parent_entity,
            template_id=template_id,
            data=value,
            context=_context,
        )

    def list_users(
        self, include: List[Literal["custom_fields"]] = None, project=None, **filters
    ):
        context = {"team_id": self.service_provider.client.team_id}
        if project:
            parent_entity = CustomFieldEntityEnum.PROJECT
            project_id = context["project_id"] = project.id
        else:
            parent_entity = CustomFieldEntityEnum.TEAM
            project_id = None
        valid_fields = generate_schema(
            UserFilters.__annotations__,
            self.service_provider.get_custom_fields_templates(
                context, CustomFieldEntityEnum.CONTRIBUTOR, parent=parent_entity
            ),
        )
        chain = QueryBuilderChain(
            [
                FieldValidationHandler(valid_fields.keys()),
                UserFilterHandler(
                    team_id=self.service_provider.client.team_id,
                    project_id=project_id,
                    service_provider=self.service_provider,
                    entity=CustomFieldEntityEnum.CONTRIBUTOR,
                    parent=parent_entity,
                ),
            ]
        )
        query = chain.handle(filters, EmptyQuery())
        if include and "custom_fields" in include:
            response = self.service_provider.work_management.list_users(
                query,
                include_custom_fields=True,
                parent_entity=parent_entity,
                project_id=project_id,
            )
            if not response.ok:
                raise AppException(response.error)
            users = response.data
            custom_fields_list = [user.custom_fields for user in users]
            serialized_fields = serialize_custom_fields(
                self.service_provider.client.team_id,
                project_id,
                self.service_provider,
                custom_fields_list,
                entity=CustomFieldEntityEnum.CONTRIBUTOR,
                parent_entity=parent_entity,
            )
            for users, serialized_custom_fields in zip(users, serialized_fields):
                users.custom_fields = serialized_custom_fields
            return response.data
        return self.service_provider.work_management.list_users(
            query, parent_entity=parent_entity, project_id=project_id
        ).data

    def update_user_activity(
        self,
        user_email: str,
        provided_projects: Union[List[int], List[str], Literal["*"]],
        action: Literal["resume", "pause"],
    ):
        if isinstance(provided_projects, list):
            if not provided_projects:
                raise AppException("Provided projects list cannot be empty.")
            body_query = EmptyQuery()
            if isinstance(provided_projects[0], int):
                body_query &= Filter("id", provided_projects, OperatorEnum.IN)
            else:
                body_query &= Filter("name", provided_projects, OperatorEnum.IN)
            exist_projects = self.service_provider.work_management.search_projects(
                body_query
            ).res_data

            # project validation
            if len(set(provided_projects)) > len(exist_projects):
                raise AppException("Invalid project(s) provided.")
        else:
            exist_projects = self.service_provider.work_management.search_projects(
                EmptyQuery()
            ).res_data

        chunked_projects_ids = divide_to_chunks([i.id for i in exist_projects], 50)
        for chunk in chunked_projects_ids:
            body_query = EmptyQuery()
            body_query &= Filter("projects.id", chunk, OperatorEnum.IN)
            body_query &= Filter(
                "projects.contributors.email", user_email, OperatorEnum.EQ
            )
            res = self.service_provider.work_management.update_user_activity(
                body_query=body_query, action=action
            )
            res.raise_for_status()

    def get_user_scores(
        self,
        project: ProjectEntity,
        item: BaseItemEntity,
        scored_user: str,
        provided_score_names: Optional[List[str]] = None,
    ):
        score_fields_res = self.service_provider.work_management.list_scores()

        # validate provided score names
        all_score_names = [s.name for s in score_fields_res.data]
        if provided_score_names and set(provided_score_names) - set(all_score_names):
            raise AppException("Please provide valid score names.")

        score_id_form_entity_map = {s.id: s for s in score_fields_res.data}

        score_values = self.service_provider.telemetry_scoring.get_score_values(
            project_id=project.id, item_id=item.id, user_id=scored_user
        )
        score_id_values_map = {s.score_id: s for s in score_values.data}

        scores = []
        for s_id, s_values in score_id_values_map.items():
            score_entity = score_id_form_entity_map.get(s_id)
            if score_entity:
                score = ScoreEntity(
                    id=s_id,
                    name=score_entity.name,
                    value=s_values.value,
                    weight=s_values.weight,
                    createdAt=score_entity.createdAt,
                    updatedAt=score_entity.updatedAt,
                )
                if provided_score_names:
                    if score_entity.name in provided_score_names:
                        scores.append(score)
                else:
                    scores.append(score)
        return scores

    @staticmethod
    def _validate_scores(scores: List[dict]) -> List[ScorePayloadEntity]:
        score_objects: List[ScorePayloadEntity] = []

        for s in scores:
            if "value" not in s:
                raise AppException("Invalid Scores.")
            try:
                score_objects.append(ScorePayloadEntity(**s))
            except AppException:
                raise
            except Exception:
                raise AppException("Invalid Scores.")

        component_ids = [score.component_id for score in score_objects]
        if len(component_ids) != len(set(component_ids)):
            raise AppException("Component IDs in scores data must be unique.")
        return score_objects

    @staticmethod
    def retrieve_scores(
        components: List[dict], score_component_ids: List[str]
    ) -> Dict[str, Dict]:
        score_component_ids = copy.copy(score_component_ids)
        found_scores = {}
        try:

            def _retrieve_score_recursive(
                all_components: List[dict], component_ids: List[str]
            ):
                for component in all_components:
                    if "children" in component:
                        _retrieve_score_recursive(component["children"], component_ids)
                    if "scoring" in component and component["id"] in component_ids:
                        component_ids.remove(component["id"])
                        found_scores[component["id"]] = {
                            "score_id": component["scoring"]["id"],
                            "user_role_name": component["scoring"]["role"]["name"],
                            "user_role": component["scoring"]["role"]["id"],
                        }

            _retrieve_score_recursive(components, score_component_ids)
        except KeyError:
            raise AppException("An error occurred while parsing the editor template.")
        return found_scores

    def set_user_scores(
        self,
        project: ProjectEntity,
        item: BaseItemEntity,
        scored_user: str,
        scores: List[Dict[str, Any]],
        components: List[dict],
    ):
        users = self.list_users(email=scored_user)
        if not users:
            raise AppException("User not found.")
        user = users[0]

        # get validate scores
        scores: List[ScorePayloadEntity] = self._validate_scores(scores)

        provided_score_component_ids = [s.component_id for s in scores]
        component_id_score_data_map = self.retrieve_scores(
            components, provided_score_component_ids
        )

        if len(component_id_score_data_map) != len(scores):
            raise AppException("Invalid component_id provided")

        scores_to_set: List[dict] = []
        for s in scores:
            score_data = {
                "item_id": item.id,
                "score_id": component_id_score_data_map[s.component_id]["score_id"],
                "user_role_name": component_id_score_data_map[s.component_id][
                    "user_role_name"
                ],
                "user_role": component_id_score_data_map[s.component_id]["user_role"],
                "user_id": user.email,
                "value": s.value,
                "weight": s.weight,
                "component_id": s.component_id,
            }
            scores_to_set.append(score_data)
        res = self.service_provider.telemetry_scoring.set_score_values(
            project_id=project.id, data=scores_to_set
        )
        if res.status_code == 400:
            res.res_error = "Please provide valid score values."
        res.raise_for_status()


class ProjectManager(BaseManager):
    def __init__(self, service_provider: ServiceProvider, team: TeamEntity):
        super().__init__(service_provider)
        self._team = team

    def get_by_id(self, project_id):
        use_case = usecases.GetProjectByIDUseCase(
            project_id=project_id, service_provider=self.service_provider
        )
        response = use_case.execute()
        return response

    def get_by_name(self, name: str):
        use_case = usecases.GetProjectByNameUseCase(
            name=name, service_provider=self.service_provider
        )
        response = use_case.execute()
        if response.errors:
            raise AppException(response.errors)
        return response

    def get_metadata(
        self,
        project: ProjectEntity,
        include_annotation_classes: bool = False,
        include_settings: bool = False,
        include_workflow: bool = False,
        include_contributors: bool = False,
        include_complete_image_count: bool = False,
        include_custom_fields: bool = False,
    ):
        use_case = usecases.GetProjectMetaDataUseCase(
            project=project,
            service_provider=self.service_provider,
            include_annotation_classes=include_annotation_classes,
            include_settings=include_settings,
            include_workflow=include_workflow,
            include_contributors=include_contributors,
            include_complete_image_count=include_complete_image_count,
            include_custom_fields=include_custom_fields,
        )
        return use_case.execute()

    def create(self, entity: ProjectEntity) -> Response:
        use_case = usecases.CreateProjectUseCase(
            project=entity, service_provider=self.service_provider
        )
        return use_case.execute()

    def list(self, condition: Condition):
        use_case = usecases.GetProjectsUseCase(
            condition=condition,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def delete(self, name: str):
        use_case = usecases.DeleteProjectUseCase(
            project_name=name, service_provider=self.service_provider
        )
        return use_case.execute()

    def update(self, entity: ProjectEntity) -> Response:
        use_case = usecases.UpdateProjectUseCase(
            entity, service_provider=self.service_provider
        )
        return use_case.execute()

    def set_settings(self, project: ProjectEntity, settings: List[SettingEntity]):
        use_case = usecases.UpdateSettingsUseCase(
            to_update=settings,
            service_provider=self.service_provider,
            project=project,
        )
        return use_case.execute()

    def list_settings(self, project: ProjectEntity):
        use_case = usecases.GetSettingsUseCase(
            service_provider=self.service_provider, project=project
        )
        return use_case.execute()

    def list_steps(self, project: ProjectEntity):
        use_case = usecases.GetStepsUseCase(
            project=project, service_provider=self.service_provider
        )
        return use_case.execute()

    def set_steps(
        self, project: ProjectEntity, steps: List, connections: List[List[int]] = None
    ):
        use_case = usecases.SetStepsUseCase(
            service_provider=self.service_provider,
            steps=steps,
            connections=connections,
            project=project,
        )
        return use_case.execute()

    def add_contributors(
        self,
        team: TeamEntity,
        project: ProjectEntity,
        contributors: List[ContributorEntity],
    ):
        project = self.get_metadata(project).data
        for contributor in contributors:
            contributor.user_role = self.service_provider.get_role_name(
                project, contributor.user_role
            )
        project = self.get_metadata(project).data
        use_case = usecases.AddContributorsToProject(
            team=team,
            project=project,
            contributors=contributors,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def un_share(self, project: ProjectEntity, user_id: str):
        use_case = usecases.UnShareProjectUseCase(
            service_provider=self.service_provider,
            project=project,
            user_id=user_id,
        )
        return use_case.execute()

    def assign_items(
        self, project: ProjectEntity, folder: FolderEntity, item_names: list, user: str
    ):
        use_case = usecases.AssignItemsUseCase(
            project=project,
            service_provider=self.service_provider,
            folder=folder,
            item_names=item_names,
            user=user,
        )
        return use_case.execute()

    def un_assign_items(
        self, project: ProjectEntity, folder: FolderEntity, item_names: list
    ):
        use_case = usecases.UnAssignItemsUseCase(
            project=project,
            service_provider=self.service_provider,
            folder=folder,
            item_names=item_names,
        )
        return use_case.execute()

    def upload_priority_scores(
        self, project: ProjectEntity, folder: FolderEntity, scores, project_folder_name
    ):
        use_case = usecases.UploadPriorityScoresUseCase(
            reporter=Reporter(),
            project=project,
            folder=folder,
            scores=scores,
            service_provider=self.service_provider,
            project_folder_name=project_folder_name,
        )
        return use_case.execute()

    @timed_lru_cache(seconds=5)
    def get_editor_template(self, project_id: int) -> dict:
        response = self.service_provider.projects.get_editor_template(
            organization_id=self._team.owner_id, project_id=project_id
        )
        response.raise_for_status()
        return response.data

    def list_projects(
        self,
        include: List[str] = None,
        **filters: Unpack[ProjectFilters],
    ) -> List[ProjectEntity]:
        valid_fields = generate_schema(
            ProjectFilters.__annotations__,
            self.service_provider.get_custom_fields_templates(
                {"team_id": self.service_provider.client.team_id},
                CustomFieldEntityEnum.PROJECT,
                parent=CustomFieldEntityEnum.TEAM,
            ),
        )
        chain = QueryBuilderChain(
            [
                FieldValidationHandler(valid_fields.keys()),
                ProjectFilterHandler(
                    team_id=self.service_provider.client.team_id,
                    project_id=None,
                    service_provider=self.service_provider,
                    entity=CustomFieldEntityEnum.PROJECT,
                    parent=CustomFieldEntityEnum.TEAM,
                ),
            ]
        )
        query = chain.handle(filters, EmptyQuery())
        include_custom_fields: bool = (
            True if include and "custom_fields" in include else False
        )
        if include_custom_fields:
            response = self.service_provider.work_management.list_projects(
                body_query=query
            )
        else:
            response = self.service_provider.work_management.search_projects(
                body_query=query
            )
        if response.error:
            raise AppException(response.error)
        projects = response.data
        if include_custom_fields:
            custom_fields_list = [project.custom_fields for project in projects]
            serialized_fields = serialize_custom_fields(
                self.service_provider.client.team_id,
                None,
                self.service_provider,
                data=custom_fields_list,
                entity=CustomFieldEntityEnum.PROJECT,
                parent_entity=CustomFieldEntityEnum.TEAM,
            )
            for project, serialized_custom_fields in zip(projects, serialized_fields):
                project.custom_fields = serialized_custom_fields
        return projects


class AnnotationClassManager(BaseManager):
    @timed_lru_cache(seconds=3600)
    def __get_auth_data(self, project: ProjectEntity, folder: FolderEntity):
        response = self.service_provider.get_s3_upload_auth_token(project, folder)
        if not response.ok:
            raise AppException(response.error)
        return response.data

    def _get_s3_repository(self, project: ProjectEntity, folder: FolderEntity):
        auth_data = self.__get_auth_data(project, folder)
        return S3Repository(
            auth_data["accessKeyId"],
            auth_data["secretAccessKey"],
            auth_data["sessionToken"],
            auth_data["bucket"],
            auth_data["region"],
        )

    def create(self, project: ProjectEntity, annotation_class: AnnotationClassEntity):
        use_case = usecases.CreateAnnotationClassUseCase(
            annotation_class=annotation_class,
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def create_multiple(
        self, project: ProjectEntity, annotation_classes: List[AnnotationClassEntity]
    ):
        use_case = usecases.CreateAnnotationClassesUseCase(
            service_provider=self.service_provider,
            annotation_classes=annotation_classes,
            project=project,
        )
        return use_case.execute()

    def list(self, condition: Condition):
        use_case = usecases.GetAnnotationClassesUseCase(
            service_provider=self.service_provider,
            condition=condition,
        )
        return use_case.execute()

    def delete(self, project: ProjectEntity, annotation_class: AnnotationClassEntity):
        use_case = usecases.DeleteAnnotationClassUseCase(
            annotation_class=annotation_class,
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def copy_multiple(
        self,
        source_project: ProjectEntity,
        source_folder: FolderEntity,
        source_item: BaseItemEntity,
        destination_project: ProjectEntity,
        destination_folder: FolderEntity,
        destination_item: BaseItemEntity,
    ):
        use_case = usecases.CopyImageAnnotationClasses(
            from_project=source_project,
            from_folder=source_folder,
            from_image=source_item,
            to_project=destination_project,
            to_folder=destination_folder,
            to_image=destination_item,
            service_provider=self.service_provider,
            from_project_s3_repo=self._get_s3_repository(source_project, source_folder),
            to_project_s3_repo=self._get_s3_repository(
                destination_project, destination_folder
            ),
        )
        return use_case.execute()

    def download(self, project: ProjectEntity, download_path: str):
        use_case = usecases.DownloadAnnotationClassesUseCase(
            project=project,
            download_path=download_path,
            service_provider=self.service_provider,
        )
        return use_case.execute()


class FolderManager(BaseManager):
    def create(self, project: ProjectEntity, folder: FolderEntity):
        use_case = usecases.CreateFolderUseCase(
            project=project,
            folder=folder,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def get_by_id(self, folder_id, project_id, team_id):
        use_case = usecases.GetFolderByIDUseCase(
            folder_id=folder_id,
            project_id=project_id,
            team_id=team_id,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def list(self, project: ProjectEntity, condition: Condition = None):
        use_case = usecases.SearchFoldersUseCase(
            project=project, service_provider=self.service_provider, condition=condition
        )
        return use_case.execute()

    def delete_multiple(self, project: ProjectEntity, folders: List[FolderEntity]):
        use_case = usecases.DeleteFolderUseCase(
            project=project,
            folders=folders,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def get_by_name(self, project: ProjectEntity, name: str = None):
        name = Controller.get_folder_name(name)
        use_case = usecases.GetFolderUseCase(
            project=project,
            folder_name=name,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def assign_users(
        self, project: ProjectEntity, folder: FolderEntity, users: List[str]
    ):
        use_case = usecases.AssignFolderUseCase(
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            users=users,
        )
        return use_case.execute()


class ItemManager(BaseManager):
    def get_by_name(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        name: str,
    ) -> BaseItemEntity:

        items = self.list_items(project, folder, name=name)
        item = next(iter(items), None)
        if not items:
            raise AppException("Item not found.")
        return item

    @staticmethod
    def _extract_value_from_mapping(data, extractor=lambda x: x):
        if isinstance(data, (list, tuple, set)):
            return [extractor(i) for i in data]
        return extractor(data)

    def _handle_special_fields(self, project: ProjectEntity, keys: List[str], val):
        """
        Handle special fields like 'approval_status', 'assignments',  'user_role' and 'annotation_status'.
        """
        if keys[0] == "approval_status":
            val = (
                [ApprovalStatus(i).value for i in val]
                if isinstance(val, (list, tuple, set))
                else ApprovalStatus(val).value
            )
        elif keys[0] == "annotation_status":
            val = self._extract_value_from_mapping(
                val,
                lambda x: self.service_provider.get_annotation_status_value(project, x),
            )
        elif keys[0] == "assignments" and keys[1] == "user_role":
            if isinstance(val, list):
                val = [self.service_provider.get_role_id(project, i) for i in val]
            else:
                val = self.service_provider.get_role_id(project, val)
        return val

    @staticmethod
    def _determine_condition_and_key(keys: List[str]) -> Tuple[OperatorEnum, str]:
        """Determine the condition and key from the filters."""
        if len(keys) == 1:
            return OperatorEnum.EQ, keys[0]
        else:
            if keys[-1].upper() in OperatorEnum.__members__:
                condition = OperatorEnum[keys.pop().upper()]
            else:
                condition = OperatorEnum.EQ
            return condition, ".".join(keys)

    def _build_query(
        self, project: ProjectEntity, filters: dict, include: List[str]
    ) -> Query:
        """Build the query object based on filters and include fields."""
        filter_annotations = ItemFilters.__annotations__.keys()
        query = EmptyQuery()
        _include = set(include if include else [])
        for key, val in filters.items():
            if key in filter_annotations:
                _keys = key.split("__")
                entity = PROJECT_ITEM_ENTITY_MAP.get(project.type, BaseItemEntity)
                if _keys[0] not in entity.__fields__:
                    _include.add(_keys[0])
                val = self._handle_special_fields(project, _keys, val)
                condition, _key = self._determine_condition_and_key(_keys)
                query &= Filter(_key, val, condition)
        for i in _include:
            query &= Join(i)
        return query

    @staticmethod
    def process_response(
        service_provider,
        items: List[BaseItemEntity],
        project: ProjectEntity,
        folder: FolderEntity,
        map_fields: bool = True,
    ) -> List[BaseItemEntity]:
        """Process the response data and return a list of serialized items."""
        data = []
        for item in items:
            if map_fields:
                item = usecases.serialize_item_entity(item, project)
                item = usecases.add_item_path(project, folder, item)
            else:
                item = usecases.serialize_item_entity(item, project, map_fields=False)
            item.annotation_status = service_provider.get_annotation_status_name(
                project, item.annotation_status
            )
            for assignment in item.assignments:
                _role = "role" if "role" in assignment else "user_role"
                user_id = "email" if "email" in assignment else "user_id"
                role_name = service_provider.get_role_name(project, assignment[_role])
                if role_name == "QA":
                    item.qa_email = assignment[user_id]
                elif role_name == "Annotator":
                    item.annotator_email = assignment[user_id]
                assignment["user_role"] = role_name
                assignment.pop("role", None)
                assignment.pop("email", None)
            data.append(item)
        return data

    def list_items(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        /,
        include: List[str] = None,
        **filters: Unpack[ItemFilters],
    ) -> List[BaseItemEntity]:

        entity = PROJECT_ITEM_ENTITY_MAP.get(project.type, BaseItemEntity)
        chain = QueryBuilderChain(
            [
                FieldValidationHandler(ItemFilters.__annotations__.keys()),
                ItemFilterHandler(
                    project=project,
                    service_provider=self.service_provider,
                    entity=entity,
                ),
                IncludeHandler(include=include),
            ]
        )
        query = chain.handle(filters, EmptyQuery())
        data = self.service_provider.item_service.list(project.id, folder.id, query)
        return self.process_response(self.service_provider, data, project, folder)

    def attach(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        attachments: List[AttachmentEntity],
        annotation_status: str = None,
    ):
        annotation_status_value = (
            self.service_provider.get_annotation_status_value(
                project, annotation_status
            )
            if annotation_status
            else None
        )
        use_case = usecases.AttachItems(
            reporter=Reporter(),
            project=project,
            folder=folder,
            attachments=attachments,
            annotation_status_value=annotation_status_value,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def generate_items(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        count: int,
        name: str,
    ):
        use_case = usecases.GenerateItems(
            reporter=Reporter(),
            project=project,
            folder=folder,
            name_prefix=name,
            count=count,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def delete(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item_names: List[str] = None,
    ):
        use_case = usecases.DeleteItemsUseCase(
            project=project,
            folder=folder,
            item_names=item_names,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def copy_multiple(
        self,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        duplicate_strategy: Literal["skip", "replace", "replace_annotations_only"],
        item_names: List[str] = None,
        include_annotations: bool = True,
    ):
        if project.type == ProjectType.PIXEL:
            use_case = usecases.CopyItems(
                reporter=Reporter(),
                project=project,
                from_folder=from_folder,
                to_folder=to_folder,
                item_names=item_names,
                service_provider=self.service_provider,
                include_annotations=include_annotations,
            )
        else:
            use_case = usecases.CopyMoveItems(
                reporter=Reporter(),
                project=project,
                from_folder=from_folder,
                to_folder=to_folder,
                item_names=item_names,
                service_provider=self.service_provider,
                include_annotations=include_annotations,
                duplicate_strategy=duplicate_strategy,
                operation="copy",
                chunk_size=500,
            )
        return use_case.execute()

    def move_multiple(
        self,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        duplicate_strategy: Literal["skip", "replace", "replace_annotations_only"],
        item_names: List[str] = None,
    ):
        if project.type == ProjectType.PIXEL:
            use_case = usecases.MoveItems(
                reporter=Reporter(),
                project=project,
                from_folder=from_folder,
                to_folder=to_folder,
                item_names=item_names,
                service_provider=self.service_provider,
            )
        else:
            use_case = usecases.CopyMoveItems(
                reporter=Reporter(),
                project=project,
                from_folder=from_folder,
                to_folder=to_folder,
                item_names=item_names,
                service_provider=self.service_provider,
                duplicate_strategy=duplicate_strategy,
                include_annotations=True,
                operation="move",
                chunk_size=500,
            )
        return use_case.execute()

    def set_annotation_statuses(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        annotation_status: str,
        item_names: List[str] = None,
    ):
        use_case = usecases.SetAnnotationStatues(
            Reporter(),
            project=project,
            folder=folder,
            annotation_status=self.service_provider.get_annotation_status_value(
                project, annotation_status
            ),
            item_names=item_names,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def set_approval_statuses(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        approval_status: str,
        item_names: List[str] = None,
    ):
        use_case = usecases.SetApprovalStatues(
            Reporter(),
            project=project,
            folder=folder,
            approval_status=approval_status,
            item_names=item_names,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def update(self, project: ProjectEntity, item: BaseItemEntity):
        item.annotation_status = self.service_provider.get_annotation_status_value(
            project, item.annotation_status
        )
        use_case = usecases.UpdateItemUseCase(
            project=project, service_provider=self.service_provider, item=item
        )
        return use_case.execute()


class AnnotationManager(BaseManager):
    def __init__(self, service_provider: ServiceProvider, config: ConfigEntity):
        super().__init__(service_provider)
        self._config = config

    def set_item_annotations(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item_id: int,
        data: dict,
        overwrite: bool,
        transform_version: str = "llmJsonV2",
        etag: str = None,
    ):
        response = self.service_provider.annotations.set_item_annotations(
            project, folder, item_id, data, overwrite, transform_version, etag
        )
        if not response.ok:
            if response.status_code == 412 and any(
                True for i in response.error if i["code"] == "PRECONDITION_FAILED"
            ):
                raise FileChangedError(
                    "The file has changed and overwrite is set to False."
                )
        response.raise_for_status()
        return response.data

    def get_item_annotations(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item_id: int,
        transform_version: str = "llmJsonV2",
    ):
        response = self.service_provider.annotations.get_item_annotations(
            project, folder, item_id, transform_version
        )
        if not response.ok:
            if response.status_code == 404:
                return None
            response.raise_for_status()
        return response

    def list(
        self,
        project: ProjectEntity,
        folder: FolderEntity = None,
        items: Union[List[str], List[int]] = None,
        verbose=True,
        transform_version: str = None,
    ):
        use_case = usecases.GetAnnotations(
            config=self._config,
            reporter=Reporter(log_info=verbose, log_warning=verbose),
            project=project,
            folder=folder,
            items=items,
            service_provider=self.service_provider,
            transform_version=transform_version,
        )
        return use_case.execute()

    def download(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        destination: str,
        recursive: bool,
        item_names: Optional[List[str]],
        callback: Optional[Callable],
        transform_version: str,
    ):
        use_case = usecases.DownloadAnnotations(
            config=self._config,
            reporter=Reporter(),
            project=project,
            folder=folder,
            destination=destination,
            recursive=recursive,
            item_names=item_names,
            service_provider=self.service_provider,
            callback=callback,
            transform_version=transform_version,
        )
        return use_case.execute()

    def download_image_annotations(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        destination: str,
    ):
        use_case = usecases.DownloadImageAnnotationsUseCase(
            project=project,
            folder=folder,
            image_name=image_name,
            service_provider=self.service_provider,
            destination=destination,
        )
        return use_case.execute()

    def delete(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item_names: Optional[List[str]] = None,
    ):
        use_case = usecases.DeleteAnnotations(
            project=project,
            folder=folder,
            service_provider=self.service_provider,
            image_names=item_names,
        )
        return use_case.execute()

    def upload_multiple(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        annotations: List[dict],
        keep_status: bool,
        user: UserEntity,
        output_format: str = None,
    ):
        if project.type == ProjectType.MULTIMODAL and output_format == "multimodal":
            use_case = usecases.UploadMultiModalAnnotationsUseCase(
                reporter=Reporter(),
                project=project,
                root_folder=folder,
                annotations=annotations,
                service_provider=self.service_provider,
                keep_status=keep_status,
                user=user,
                transform_version="llmJsonV2",
            )
        else:
            use_case = usecases.UploadAnnotationsUseCase(
                reporter=Reporter(),
                project=project,
                folder=folder,
                annotations=annotations,
                service_provider=self.service_provider,
                keep_status=keep_status,
                user=user,
                transform_version=None,
            )
        return use_case.execute()

    def upload_from_folder(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        annotation_paths: List[str],
        user: UserEntity,
        keep_status: bool = False,
        client_s3_bucket=None,
        is_pre_annotations: bool = False,
        folder_path: str = None,
    ):
        use_case = usecases.UploadAnnotationsFromFolderUseCase(
            project=project,
            folder=folder,
            user=user,
            annotation_paths=annotation_paths,
            service_provider=self.service_provider,
            pre_annotation=is_pre_annotations,
            client_s3_bucket=client_s3_bucket,
            reporter=Reporter(),
            folder_path=folder_path,
            keep_status=keep_status,
        )
        return use_case.execute()

    def upload_image_annotations(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image: ImageEntity,
        user: UserEntity,
        annotations: dict,
        mask: io.BytesIO = None,
        verbose: bool = True,
        keep_status: bool = False,
    ):
        use_case = usecases.UploadAnnotationUseCase(
            project=project,
            folder=folder,
            user=user,
            service_provider=self.service_provider,
            image=image,
            annotations=annotations,
            mask=mask,
            verbose=verbose,
            reporter=Reporter(),
            keep_status=keep_status,
        )
        return use_case.execute()


class CustomFieldManager(BaseManager):
    def create_schema(self, project: ProjectEntity, schema: dict):
        use_case = usecases.CreateCustomSchemaUseCase(
            reporter=Reporter(),
            project=project,
            schema=schema,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def get_schema(self, project: ProjectEntity):
        use_case = usecases.GetCustomSchemaUseCase(
            reporter=Reporter(),
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def delete_schema(self, project: ProjectEntity, fields: List[str]):
        use_case = usecases.DeleteCustomSchemaUseCase(
            reporter=Reporter(),
            project=project,
            fields=fields,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def upload_values(
        self, project: ProjectEntity, folder: FolderEntity, items: List[dict]
    ):
        use_case = usecases.UploadCustomValuesUseCase(
            reporter=Reporter(),
            project=project,
            folder=folder,
            items=items,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def delete_values(
        self, project: ProjectEntity, folder: FolderEntity, items: List[dict]
    ):
        use_case = usecases.DeleteCustomValuesUseCase(
            reporter=Reporter(),
            project=project,
            folder=folder,
            items=items,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def list_fields(
        self, project: ProjectEntity, item_ids: List[int]
    ) -> Dict[int, dict]:
        _data: Dict[int, dict] = dict()
        for chunk in divide_to_chunks(
            item_ids, self.service_provider.explore.CHUNK_SIZE
        ):
            response = self.service_provider.explore.list_fields(project, chunk)
            if not response.ok:
                raise AppException(response.error)
            for item_id, fields in response.data.items():
                _data[int(item_id)] = {**{k: v for d in fields for k, v in d.items()}}
        return _data


class IntegrationManager(BaseManager):
    def list(self):
        use_case = usecases.GetIntegrations(
            reporter=Reporter(), service_provider=self.service_provider
        )
        return use_case.execute()

    def attach_items(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        integration: IntegrationEntity,
        folder_path: str = None,
        query: Optional[str] = None,
        item_name_column: Optional[str] = None,
        custom_item_name: Optional[str] = None,
        component_mapping: Optional[Dict[str, str]] = None,
    ):
        use_case = usecases.AttachIntegrations(
            reporter=Reporter(),
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            integration=integration,
            folder_path=folder_path,
            query=query,
            item_name_column=item_name_column,
            custom_item_name=custom_item_name,
            component_mapping=component_mapping,
        )
        return use_case.execute()


class SubsetManager(BaseManager):
    def list(self, project: ProjectEntity):
        use_case = usecases.ListSubsetsUseCase(
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def add_items(self, project: ProjectEntity, subset: str, items: List[dict]):
        root_folder = FolderEntity(id=project.id, name="root")
        use_case = usecases.AddItemsToSubsetUseCase(
            reporter=Reporter(),
            project=project,
            subset_name=subset,
            items=items,
            service_provider=self.service_provider,
            root_folder=root_folder,
        )

        return use_case.execute()


class BaseController(metaclass=ABCMeta):
    SESSIONS = {}

    def __init__(self, config: ConfigEntity):
        self._config = config
        self._logger = logging.getLogger("sa")
        self._testing = os.getenv("SA_TESTING", "False").lower() in ("true", "1", "t")
        self._token = config.API_TOKEN
        self._team_data = None
        self._s3_upload_auth_data = None
        self._projects = None
        self._folders = None
        self._teams = None
        self._images = None
        self._items = None
        self._integrations = None
        self._user_id = None
        self._reporter = None

        http_client = HttpClient(
            api_url=config.API_URL, token=config.API_TOKEN, verify_ssl=config.VERIFY_SSL
        )

        self.service_provider = ServiceProvider(http_client)
        self._user = self.get_current_user()
        self._team = self.get_team().data
        self.annotation_classes = AnnotationClassManager(self.service_provider)
        self.projects = ProjectManager(self.service_provider, team=self._team)
        self.work_management = WorkManagementManager(self.service_provider)
        self.folders = FolderManager(self.service_provider)
        self.items = ItemManager(self.service_provider)
        self.annotations = AnnotationManager(self.service_provider, config)
        self.custom_fields = CustomFieldManager(self.service_provider)
        self.subsets = SubsetManager(self.service_provider)
        self.integrations = IntegrationManager(self.service_provider)

    @property
    def reporter(self):
        return self._reporter

    @property
    def org_id(self):
        return self._team.owner_id

    @property
    def current_user(self):
        return self._user

    @property
    def user_id(self):
        if not self._user_id:
            self._user_id, _ = self.get_team()
        return self._user_id

    @property
    def team(self):
        return self._team

    def get_team(self):
        return usecases.GetTeamUseCase(
            service_provider=self.service_provider, team_id=self.team_id
        ).execute()

    def get_current_user(self) -> UserEntity:
        response = usecases.GetCurrentUserUseCase(
            service_provider=self.service_provider, team_id=self.team_id
        ).execute()
        if response.errors:
            raise AppException(response.errors)
        return response.data

    @property
    def team_data(self):
        if not self._team_data:
            self._team_data = self.team
        return self._team_data

    @property
    def team_id(self) -> int:
        if not self._token:
            raise AppException("Invalid credentials provided.")
        return int(self._token.split("=")[-1])

    @staticmethod
    def get_default_reporter(
        log_info: bool = True,
        log_warning: bool = True,
        disable_progress_bar: bool = False,
        log_debug: bool = True,
    ) -> Reporter:
        return Reporter(log_info, log_warning, disable_progress_bar, log_debug)

    @property
    def s3_repo(self):
        return S3Repository


class Controller(BaseController):
    DEFAULT = None

    @classmethod
    def set_default(cls, obj):
        cls.DEFAULT = obj
        return cls.DEFAULT

    def get_folder_by_id(self, folder_id: int, project_id: int):
        response = self.folders.get_by_id(
            folder_id=folder_id, project_id=project_id, team_id=self.team_id
        )
        return response

    def get_project_by_id(self, project_id: int):
        response = self.projects.get_by_id(project_id=project_id)
        if response.errors:
            raise AppException("Project not found.")
        return response

    def get_item_by_id(self, item_id: int, project: ProjectEntity) -> BaseItemEntity:
        response = self.service_provider.item_service.get(
            project_id=project.id, item_id=item_id
        )
        if response.error:
            raise AppException(response.error)
        PROJECT_TYPE_RESPONSE_MAP[project.type] = response.data
        item = serialize_item_entity(response.data, project)
        item.annotation_status = self.service_provider.get_annotation_status_name(
            project, item.annotation_status
        )
        return item

    def get_project_folder_by_path(
        self, path: Union[str, Path]
    ) -> Tuple[ProjectEntity, FolderEntity]:
        project_name, folder_name = extract_project_folder(path)
        return self.get_project_folder((project_name, folder_name))

    def get_project(self, name: str) -> ProjectEntity:
        project = self.projects.get_by_name(name).data
        if not project:
            raise AppException("Project not found.")
        return project

    def get_folder(self, project: ProjectEntity, name: str = None) -> FolderEntity:
        folder = self.folders.get_by_name(project, name).data
        if not folder:
            raise AppException("Folder not found.")
        return folder

    @staticmethod
    def get_folder_name(name: str = None):
        if name:
            return name
        return "root"

    def upload_image_to_project(
        self,
        project_name: str,
        folder_name: str,
        image_name: str,
        image: Union[str, io.BytesIO] = None,
        annotation_status: str = None,
        image_quality_in_editor: str = None,
        from_s3_bucket=None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)
        image_bytes = None
        image_path = None
        if isinstance(image, (str, Path)):
            image_path = image
        else:
            image_bytes = image
        annotation_status_value = (
            self.service_provider.get_annotation_status_value(
                project, annotation_status
            )
            if annotation_status
            else None
        )
        return usecases.UploadImageToProject(
            project=project,
            folder=folder,
            s3_repo=self.s3_repo,
            service_provider=self.service_provider,
            image_path=image_path,
            image_bytes=image_bytes,
            image_name=image_name,
            from_s3_bucket=from_s3_bucket,
            annotation_status_value=annotation_status_value,
            image_quality_in_editor=image_quality_in_editor,
        ).execute()

    def upload_images_to_project(
        self,
        project_name: str,
        folder_name: str,
        paths: List[str],
        annotation_status: str = None,
        image_quality_in_editor: str = None,
        from_s3_bucket=None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)

        return usecases.UploadImagesToProject(
            project=project,
            folder=folder,
            s3_repo=self.s3_repo,
            service_provider=self.service_provider,
            paths=paths,
            from_s3_bucket=from_s3_bucket,
            annotation_status_value=self.service_provider.get_annotation_status_value(
                project, annotation_status
            ),
            image_quality_in_editor=image_quality_in_editor,
        )

    def upload_images_from_folder_to_project(
        self,
        project: ProjectEntity,
        folder_name: str,
        folder_path: str,
        extensions: Optional[List[str]] = None,
        annotation_status: str = None,
        exclude_file_patterns: Optional[List[str]] = None,
        recursive_sub_folders: Optional[bool] = None,
        image_quality_in_editor: str = None,
        from_s3_bucket=None,
    ):
        folder = self.get_folder(project, folder_name)
        annotation_status_value = (
            self.service_provider.get_annotation_status_value(
                project, annotation_status
            )
            if annotation_status
            else None
        )
        return usecases.UploadImagesFromFolderToProject(
            project=project,
            folder=folder,
            s3_repo=self.s3_repo,
            service_provider=self.service_provider,
            folder_path=folder_path,
            extensions=extensions,
            annotation_status_value=annotation_status_value,
            from_s3_bucket=from_s3_bucket,
            exclude_file_patterns=exclude_file_patterns,
            recursive_sub_folders=recursive_sub_folders,
            image_quality_in_editor=image_quality_in_editor,
        )

    def prepare_export(
        self,
        project_name: str,
        folder_names: List[str],
        include_fuse: bool,
        only_pinned: bool,
        annotation_statuses: List[str] = None,
        integration_id: int = None,
        export_type: int = None,
    ):
        project = self.get_project(project_name)
        use_case = usecases.PrepareExportUseCase(
            project=project,
            folder_names=folder_names,
            service_provider=self.service_provider,
            include_fuse=include_fuse,
            only_pinned=only_pinned,
            annotation_statuses=annotation_statuses,
            integration_id=integration_id,
            export_type=export_type,
        )
        return use_case.execute()

    def search_team_contributors(self, **kwargs):
        condition = build_condition(**kwargs)
        use_case = usecases.SearchContributorsUseCase(
            service_provider=self.service_provider,
            team_id=self.team_id,
            condition=condition,
        )
        return use_case.execute()

    def _get_image(
        self,
        project: ProjectEntity,
        image_name: str,
        folder: FolderEntity = None,
    ) -> ImageEntity:
        response = usecases.GetImageUseCase(
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            image_name=image_name,
        ).execute()
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def update(self, project: ProjectEntity, folder: FolderEntity):
        use_case = usecases.UpdateFolderUseCase(
            service_provider=self.service_provider, folder=folder, project=project
        )
        return use_case.execute()

    def un_assign_folder(self, project_name: str, folder_name: str):
        project_entity = self.get_project(project_name)
        folder = self.get_folder(project_entity, folder_name)
        use_case = usecases.UnAssignFolderUseCase(
            service_provider=self.service_provider,
            project=project_entity,
            folder=folder,
        )
        return use_case.execute()

    def get_exports(self, project_name: str, return_metadata: bool):
        project = self.get_project(project_name)

        use_case = usecases.GetExportsUseCase(
            service_provider=self.service_provider,
            project=project,
            return_metadata=return_metadata,
        )
        return use_case.execute()

    def download_image(
        self,
        project_name: str,
        image_name: str,
        download_path: str,
        folder_name: str = None,
        image_variant: str = None,
        include_annotations: bool = None,
        include_fuse: bool = None,
        include_overlay: bool = None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)
        image = self._get_image(project, image_name, folder)

        use_case = usecases.DownloadImageUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            image=image,
            service_provider=self.service_provider,
            download_path=download_path,
            image_variant=image_variant,
            include_annotations=include_annotations,
            include_fuse=include_fuse,
            include_overlay=include_overlay,
        )
        return use_case.execute()

    def download_export(
        self,
        project_name: str,
        export_name: str,
        folder_path: str,
        extract_zip_contents: bool,
        to_s3_bucket: bool,
    ):
        project = self.get_project(project_name)
        use_case = usecases.DownloadExportUseCase(
            service_provider=self.service_provider,
            project=project,
            export_name=export_name,
            folder_path=folder_path,
            extract_zip_contents=extract_zip_contents,
            to_s3_bucket=to_s3_bucket,
            reporter=self.get_default_reporter(),
        )
        return use_case.execute()

    def consensus(
        self,
        project_name: str,
        folder_names: list,
        # export_path: str,
        image_list: list,
        annot_type: str,
        # show_plots: bool,
    ):
        project = self.get_project(project_name)

        use_case = usecases.ConsensusUseCase(
            project=project,
            folder_names=folder_names,
            image_list=image_list,
            annotation_type=annot_type,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def validate_annotations(self, project_type: str, annotation: dict):
        use_case = usecases.ValidateAnnotationUseCase(
            reporter=self.get_default_reporter(),
            project_type=constances.ProjectType(project_type).value,
            annotation=annotation,
            team_id=self.team_id,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def invite_contributors_to_team(self, emails: list, set_admin: bool):
        use_case = usecases.InviteContributorsToTeam(
            team=self.team,
            emails=emails,
            set_admin=set_admin,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def upload_videos(
        self,
        project_name: str,
        folder_name: str,
        paths: List[str],
        start_time: float,
        extensions: List[str] = None,
        exclude_file_patterns: List[str] = None,
        end_time: Optional[float] = None,
        target_fps: Optional[int] = None,
        annotation_status: Optional[str] = None,
        image_quality_in_editor: Optional[str] = None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)
        annotation_status_value = (
            self.service_provider.get_annotation_status_value(
                project, annotation_status
            )
            if annotation_status
            else None
        )
        use_case = usecases.UploadVideosAsImages(
            reporter=self.get_default_reporter(),
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            s3_repo=self.s3_repo,
            paths=paths,
            target_fps=target_fps,
            extensions=extensions,
            exclude_file_patterns=exclude_file_patterns,
            start_time=start_time,
            end_time=end_time,
            annotation_status_value=annotation_status_value,
            image_quality_in_editor=image_quality_in_editor,
        )
        return use_case.execute()

    def get_annotations_per_frame(
        self, project_name: str, folder_name: str, video_name: str, fps: int
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)

        use_case = usecases.GetVideoAnnotationsPerFrame(
            config=self._config,
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            video_name=video_name,
            fps=fps,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def query_entities(
        self, project_name: str, folder_name: str, query: str = None, subset: str = None
    ) -> List[BaseItemEntity]:
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)

        use_case = usecases.QueryEntitiesUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            query=query,
            subset=subset,
            service_provider=self.service_provider,
        )
        response = use_case.execute()
        if response.errors:
            raise AppException(response.errors)
        items = response.data
        return ItemManager.process_response(
            self.service_provider, items, project, folder, map_fields=False
        )

    def query_items_count(self, project_name: str, query: str = None) -> int:
        project = self.get_project(project_name)

        use_case = usecases.QueryEntitiesCountUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            query=query,
            service_provider=self.service_provider,
        )
        response = use_case.execute()
        if response.errors:
            raise AppException(response.errors)
        return response.data["count"]

    def get_project_folder(
        self, path: Union[str, Tuple[int, int], Tuple[str, str]]
    ) -> Tuple[ProjectEntity, Optional[FolderEntity]]:
        if isinstance(path, str):
            project_name, folder_name = extract_project_folder(path)
            project = self.get_project(project_name)
            return project, self.get_folder(project, folder_name)

        if isinstance(path, tuple) and len(path) == 2:
            project_pk, folder_pk = path
            if all(isinstance(x, int) for x in path):
                return (
                    self.get_project_by_id(project_pk).data,
                    self.get_folder_by_id(folder_pk, project_pk).data,
                )
            if all(isinstance(x, str) for x in path):
                project = self.get_project(project_pk)
                return project, self.get_folder(project, folder_pk)

        raise AppException("Provided project param is not valid.")

    def get_item(
        self, project: ProjectEntity, folder: FolderEntity, item: Union[int, str]
    ) -> BaseItemEntity:
        if isinstance(item, int):
            return self.get_item_by_id(item_id=item, project=project)
        else:
            return self.items.get_by_name(project, folder, item)
