from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import AnnotationClassListResponse
from lib.core.service_types import ServiceResponse
from lib.core.serviceproviders import BaseAnnotationClassService


class AnnotationClassService(BaseAnnotationClassService):
    URL_LIST = "classes"
    URL_GET = "class/{}"

    def create_multiple(
        self,
        project: entities.ProjectEntity,
        classes: List[entities.AnnotationClassEntity],
    ):
        params = {
            "project_id": project.id,
        }
        return self.client.request(
            self.URL_LIST,
            "post",
            params=params,
            data={
                # "classes": [json.loads(i.json(exclude_none=True, exclude_unset=True)) for i in data]
                "classes": classes
            },
            content_type=AnnotationClassListResponse,
        )

    def list(self, condition: Condition = None) -> ServiceResponse:
        return self.client.paginate(
            url=f"{self.URL_LIST}?{condition.build_query()}"
            if condition
            else self.URL_LIST,
            item_type=entities.AnnotationClassEntity,
        )

    def create(
        self, project_id: int, item: entities.AnnotationClassEntity
    ) -> ServiceResponse:
        params = {"project_id": project_id}
        response = self.client.request(
            self.URL_LIST, "post", params=params, data={"classes": [item]}
        )
        if not response.ok or not response.data:
            return response
        response.res_data = response.data[0]
        return response

    def delete(self, project_id: int, annotation_class_id: int) -> ServiceResponse:
        return self.client.request(
            self.URL_GET.format(annotation_class_id),
            "delete",
            params={"project_id": project_id},
        )
