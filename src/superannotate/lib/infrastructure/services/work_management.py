import base64
import json
from typing import List

from lib.core.entities import CategoryEntity
from lib.core.entities import WorkflowEntity
from lib.core.entities.work_managament import WMProjectEntity
from lib.core.exceptions import AppException
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import OperatorEnum
from lib.core.jsx_conditions import Query
from lib.core.service_types import ListCategoryResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import WMProjectListResponse
from lib.core.service_types import WMUserListResponse
from lib.core.serviceproviders import BaseWorkManagementService


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
    URL_CUSTOM_FIELD_TEMPLATE_DELETE = "customfieldtemplates/{template_id}"
    URL_PROJECT_CUSTOM_ENTITIES = "customentities/{project_id}"
    SEARCH_CUSTOM_ENTITIES = "customentities/search"

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

    def list_project_custom_field_templates(self):
        return self.client.request(
            url=self.URL_CUSTOM_FIELD_TEMPLATES,
            method="get",
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

    def delete_project_custom_field_template(self, pk: int):
        return self.client.request(
            url=self.URL_CUSTOM_FIELD_TEMPLATE_DELETE.format(template_id=pk),
            method="delete",
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
            url=self.URL_PROJECT_CUSTOM_ENTITIES.format(project_id=project_id),
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

    def set_project_custom_field_value(self, project_id: int, data: dict):
        return self.client.request(
            url=self.URL_PROJECT_CUSTOM_ENTITIES.format(project_id=project_id),
            method="patch",
            headers={
                "x-sa-entity-context": self._generate_context(
                    team_id=self.client.team_id, project_id=project_id
                ),
            },
            data={"customField": {"custom_field_values": data}},
            params={
                "entity": "Project",
                "parentEntity": "Team",
            },
        )

    def list_projects(self, body_query: Query, chunk_size=100) -> WMProjectListResponse:
        return self.client.jsx_paginate(
            url=self.SEARCH_CUSTOM_ENTITIES,
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

    def list_users(self, body_query: Query, chunk_size=100) -> WMUserListResponse:
        return self.client.jsx_paginate(
            url=self.SEARCH_CUSTOM_ENTITIES,
            method="post",
            body_query=body_query,
            query_params={
                "entity": "Contributor",
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
