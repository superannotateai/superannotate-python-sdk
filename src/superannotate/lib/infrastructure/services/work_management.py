import base64

from lib.core.entities import WorkflowEntity
from lib.core.entities.work_managament import WMProjectEntity
from lib.core.exceptions import AppException
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import OperatorEnum
from lib.core.jsx_conditions import Query
from lib.core.service_types import WMProjectListResponse
from lib.core.serviceproviders import BaseWorkManagementService


class WorkManagementService(BaseWorkManagementService):
    URL_GET = "workflows/{project_id}"
    URL_LIST = "workflows"
    URL_LIST_STATUSES = "workflows/{workflow_id}/workflowstatuses"
    URL_LIST_ROLES = "workflows/{workflow_id}/workflowroles"
    URL_CREATE_ROLE = "roles"
    URL_CREATE_STATUS = "statuses"
    URL_CUSTOM_FIELD_TEMPLATES = "customfieldtemplates"
    URL_CUSTOM_FIELD_TEMPLATE_DELETE = "customfieldtemplates/{template_id}"
    URL_PROJECT_CUSTOM_ENTITIES = "customentities/{project_id}"
    LIST_PROJECTS = "customentities/search"

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
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id}}}'.encode("utf-8")
                ).decode()
            },
        )
        return result

    def list_workflow_statuses(self, project_id: int, workflow_id: int):
        return self.client.request(
            url=self.URL_LIST_STATUSES.format(workflow_id=workflow_id),
            method="get",
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},"project_id":{project_id}}}'.encode(
                        "utf-8"
                    )
                ).decode()
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
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},"project_id":{project_id}}}'.encode(
                        "utf-8"
                    )
                ).decode()
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
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},"organization_id":"{org_id}"}}'.encode(
                        "utf-8"
                    )
                ).decode()
            },
            data=data,
        )

    def create_custom_status(self, org_id: str, data: dict):
        return self.client.request(
            url=self.URL_CREATE_STATUS,
            method="post",
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},"organization_id":"{org_id}"}}'.encode(
                        "utf-8"
                    )
                ).decode()
            },
            data=data,
        )

    def list_project_custom_field_templates(self):
        return self.client.request(
            url=self.URL_CUSTOM_FIELD_TEMPLATES,
            method="get",
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id}}}'.encode("utf-8")
                ).decode()
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
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id}}}'.encode("utf-8")
                ).decode()
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
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id}}}'.encode("utf-8")
                ).decode()
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
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},"project_id":{project_id}}}'.encode(
                        "utf-8"
                    )
                ).decode()
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
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},"project_id":{project_id}}}'.encode(
                        "utf-8"
                    )
                ).decode()
            },
            data={"customField": {"custom_field_values": data}},
            params={
                "entity": "Project",
                "parentEntity": "Team",
            },
        )

    def list_projects(self, body_query: Query, chunk_size=100) -> WMProjectListResponse:
        return self.client.jsx_paginate(
            url=self.LIST_PROJECTS,
            method="post",
            body_query=body_query,
            query_params={
                "entity": "Project",
                "parentEntity": "Team",
            },
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id}}}'.encode("utf-8")
                ).decode()
            },
            chunk_size=chunk_size,
            item_type=WMProjectEntity,
        )
