import base64

from lib.core.entities import WorkflowEntity
from lib.core.exceptions import AppException
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import OperatorEnum
from lib.core.jsx_conditions import Query
from lib.core.serviceproviders import BaseWorkManagementService


class WorkManagementService(BaseWorkManagementService):
    URL_GET = "workflows/{project_id}"
    URL_LIST = "workflows"
    URL_LIST_STATUSES = "workflows/{workflow_id}/workflowstatuses"
    URL_LIST_ROLES = "workflows/{workflow_id}/workflowroles"
    URL_CREATE_ROLE = "roles"
    URL_CREATE_STATUS = "statuses"

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
