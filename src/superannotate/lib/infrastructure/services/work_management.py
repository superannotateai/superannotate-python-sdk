import base64
import json
from typing import List
from typing import Literal
from typing import Optional

from lib.core.entities import CategoryEntity
from lib.core.entities import WorkflowEntity
from lib.core.entities.work_managament import WMProjectEntity
from lib.core.entities.work_managament import WMProjectUserEntity
from lib.core.entities.work_managament import WMScoreEntity
from lib.core.entities.work_managament import WMUserEntity
from lib.core.enums import CustomFieldEntityEnum
from lib.core.exceptions import AppException
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import OperatorEnum
from lib.core.jsx_conditions import Query
from lib.core.service_types import ListCategoryResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import WMCustomFieldResponse
from lib.core.service_types import WMProjectListResponse
from lib.core.service_types import WMScoreListResponse
from lib.core.service_types import WMUserListResponse
from lib.core.serviceproviders import BaseWorkManagementService


def prepare_validation_error(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if res.error and isinstance(res.error, list):
            if res.error[0].get("code") == "VALIDATION_ERROR":
                error_types_map = {
                    "Array": "list",
                    "string": "str",
                    "number": "numeric",
                }
                valid_types = res.error[0]["details"]["valid_types"]
                prepared_valid_types = [error_types_map.get(i, i) for i in valid_types]
                error_msg = (
                    f"Invalid input: The provided value is not valid.\n"
                    f"Expected type: {' or '.join(prepared_valid_types)}."
                )
                expected_values = res.error[0]["details"].get("expected_values")
                if expected_values:
                    error_msg += f"\nValid options are: {', '.join(expected_values)}."
                res.res_error = error_msg
        res.raise_for_status()

    return wrapper


class WorkManagementService(BaseWorkManagementService):
    URL_GET = "workflows/{project_id}"
    URL_LIST = "workflows"
    URL_LIST_STATUSES = "workflows/{workflow_id}/workflowstatuses"
    URL_LIST_ROLES = "workflows/{workflow_id}/workflowroles"
    URL_CREATE_ROLE = "roles"
    URL_CREATE_STATUS = "statuses"
    URL_LIST_CATEGORIES = "categories"
    URL_CREATE_CATEGORIES = "categories/bulk"
    URL_CUSTOM_FIELD_TEMPLATES = "customfieldtemplates"
    URL_SCORES = "scores"
    URL_DELETE_SCORE = "scores/{score_id}"
    URL_CUSTOM_FIELD_TEMPLATE_DELETE = "customfieldtemplates/{template_id}"
    URL_SET_CUSTOM_ENTITIES = "customentities/{pk}"
    URL_SEARCH_CUSTOM_ENTITIES = "customentities/search"
    URL_SEARCH_TEAM_USERS = "teamusers/search"
    URL_SEARCH_PROJECT_USERS = "projectusers/search"
    URL_SEARCH_PROJECTS = "projects/search"
    URL_RESUME_PAUSE_USER = "teams/editprojectsusers"

    @staticmethod
    def _generate_context(**kwargs):
        encoded_context = base64.b64encode(json.dumps(kwargs).encode("utf-8"))
        return encoded_context.decode("utf-8")

    def list_project_categories(self, project_id: int) -> ListCategoryResponse:
        return self.client.paginate(
            self.URL_LIST_CATEGORIES,
            item_type=CategoryEntity,
            query_params={"project_id": project_id},
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id
                ),
            },
        )

    def create_project_categories(
        self, project_id: int, categories: List[str]
    ) -> ServiceResponse:
        response = self.client.request(
            method="post",
            url=self.URL_CREATE_CATEGORIES,
            params={"project_id": project_id},
            data={"bulk": [{"name": i} for i in categories]},
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, project_id=project_id
                ),
            },
        )
        response.raise_for_status()
        return response

    def get_workflow(self, pk: int) -> WorkflowEntity:
        response = self.list_workflows(Filter("id", pk, OperatorEnum.EQ))
        if response.error:
            raise AppException(response.error)
        for w in response.data:
            if w.id == pk:
                return w

    def list_workflows(self, query: Query):
        result = self.client.paginate(
            f"{self.URL_LIST}?{query.build_query()}",
            item_type=WorkflowEntity,
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id
                ),
            },
        )
        return result

    def list_workflow_statuses(self, project_id: int, workflow_id: int):
        return self.client.request(
            url=self.URL_LIST_STATUSES.format(workflow_id=workflow_id),
            method="get",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, project_id=project_id
                )
            },
            params={
                "join": "status",
            },
        )

    def list_workflow_roles(self, project_id: int, workflow_id: int):
        return self.client.request(
            url=self.URL_LIST_ROLES.format(workflow_id=workflow_id),
            method="get",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, project_id=project_id
                )
            },
            params={
                "join": "role",
            },
        )

    def create_custom_role(self, org_id: str, data: dict):
        return self.client.request(
            url=self.URL_CREATE_ROLE,
            method="post",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, organization_id=org_id
                )
            },
            data=data,
        )

    def create_custom_status(self, org_id: str, data: dict):
        return self.client.request(
            url=self.URL_CREATE_STATUS,
            method="post",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, organization_id=org_id
                )
            },
            data=data,
        )

    def list_custom_field_templates(
        self,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
        context: dict = None,
    ):
        if context is None:
            context = {}
        return self.client.request(
            url=self.URL_CUSTOM_FIELD_TEMPLATES,
            method="get",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, **context
                ),
            },
            params={
                "entity": entity.value,
                "parentEntity": parent_entity.value,
            },
        )

    def create_project_custom_field_template(self, data: dict):
        return self.client.request(
            url=self.URL_CUSTOM_FIELD_TEMPLATES,
            method="post",
            data=data,
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id
                ),
            },
            params={
                "entity": "Project",
                "parentEntity": "Team",
            },
        )

    def list_project_custom_entities(self, project_id: int):
        return self.client.request(
            url=self.URL_SET_CUSTOM_ENTITIES.format(pk=project_id),
            method="get",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, project_id=project_id
                ),
            },
            params={
                "entity": "Project",
                "parentEntity": "Team",
            },
        )

    def list_projects(self, body_query: Query, chunk_size=100) -> WMProjectListResponse:
        """list projects include custom_fields"""
        return self.client.jsx_paginate(
            url=self.URL_SEARCH_CUSTOM_ENTITIES,
            method="post",
            body_query=body_query,
            query_params={
                "entity": "Project",
                "parentEntity": "Team",
            },
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id
                ),
            },
            chunk_size=chunk_size,
            item_type=WMProjectEntity,
        )

    def search_projects(
        self, body_query: Query, chunk_size=100
    ) -> WMProjectListResponse:
        """list projects without custom_fields"""
        return self.client.jsx_paginate(
            url=self.URL_SEARCH_PROJECTS,
            method="post",
            body_query=body_query,
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id
                ),
            },
            chunk_size=chunk_size,
            item_type=WMProjectEntity,
        )

    def list_users(
        self,
        body_query: Query,
        chunk_size=100,
        parent_entity: str = "Team",
        project_id: int = None,
        include_custom_fields=False,
    ) -> WMUserListResponse:
        if include_custom_fields:
            url = self.URL_SEARCH_CUSTOM_ENTITIES
        else:
            if parent_entity == "Team":
                url = self.URL_SEARCH_TEAM_USERS
            else:
                url = self.URL_SEARCH_PROJECT_USERS
        if project_id is None:
            user_entity = WMUserEntity
            entity_context = self._generate_context(team_id=self.client.team_id)
        else:
            user_entity = WMProjectUserEntity
            entity_context = self._generate_context(
                team_id=self.client.team_id,
                project_id=project_id,
            )
        return self.client.jsx_paginate(
            url=url,
            method="post",
            body_query=body_query,
            query_params={
                "entity": "Contributor",
                "parentEntity": parent_entity,
            },
            headers={
                "x-sa-entity-context": entity_context,
            },
            chunk_size=chunk_size,
            item_type=user_entity,
        )

    def create_custom_field_template(
        self,
        name: str,
        component_id: int,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
        component_payload: dict = None,
        access: dict = None,
        entity_context: Optional[dict] = None,
    ) -> WMCustomFieldResponse:
        if entity_context is None:
            entity_context = {}
        return self.client.request(
            method="post",
            url=self.URL_CUSTOM_FIELD_TEMPLATES,
            params={
                "entity": entity.value,
                "parentEntity": parent_entity.value,
            },
            data={
                "name": name,
                "component_id": component_id,
                "component_payload": component_payload
                if component_payload is not None
                else {},
                "access": access if access is not None else {},
            },
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, **entity_context
                ),
            },
        )

    def delete_custom_field_template(
        self,
        pk: int,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
        entity_context: Optional[dict] = None,
    ):
        if entity_context is None:
            entity_context = {}
        response = self.client.request(
            method="delete",
            url=self.URL_CUSTOM_FIELD_TEMPLATE_DELETE.format(template_id=pk),
            params={
                "entity": entity,
                "parentEntity": parent_entity,
            },
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, **entity_context
                ),
            },
        )
        response.raise_for_status()

    @prepare_validation_error
    def set_custom_field_value(
        self,
        entity_id: int,
        template_id: int,
        data: dict,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
        context: Optional[dict] = None,
    ):
        return self.client.request(
            url=self.URL_SET_CUSTOM_ENTITIES.format(pk=entity_id),
            method="patch",
            headers={
                "x-sa-entity-context": self._generate_context(**context),
            },
            data={"customField": {"custom_field_values": {template_id: data}}},
            params={
                "entity": entity.value,
                "parentEntity": parent_entity.value,
            },
        )

    def update_user_activity(
        self, body_query: Query, action=Literal["resume", "pause"]
    ) -> ServiceResponse:
        """resume or pause user by projects"""
        body = body_query.body_builder()
        body["body"] = {
            "projectUsers": {"permissions": {"paused": 1 if action == "pause" else 0}}
        }
        return self.client.request(
            url=self.URL_RESUME_PAUSE_USER,
            method="post",
            data=body,
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id
                ),
            },
        )

    def list_scores(self) -> WMScoreListResponse:
        return self.client.paginate(
            url=self.URL_SCORES,
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id
                ),
            },
            item_type=WMScoreEntity,
        )

    def create_score(
        self,
        name: str,
        description: Optional[str],
        score_type: Literal["rating", "number", "radio"],
        payload: dict,
    ) -> ServiceResponse:
        data = {
            "name": name,
            "description": description,
            "type": score_type,
            "payload": payload,
        }
        return self.client.request(
            url=self.URL_SCORES,
            method="post",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=int(self.client.team_id)  # TODO delete int after BED fix
                ),
            },
            data=data,
        )

    def delete_score(self, score_id: int) -> ServiceResponse:
        return self.client.request(
            url=self.URL_DELETE_SCORE.format(score_id=score_id),
            method="delete",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id
                ),
            },
        )
