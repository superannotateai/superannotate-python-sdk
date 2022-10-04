from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import ServiceResponse
from lib.core.serviceproviders import BaseAnnotationClassService


class AnnotationClassService(BaseAnnotationClassService):
    URL_LIST = "classes"
    URL_GET = "class/{}"

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
        response.data = response.data[0]
        return response

    def create_multiple(
        self, project_id: int, items: List[entities.AnnotationClassEntity]
    ) -> ServiceResponse:
        params = {"project_id": project_id}
        return self.client.request(
            self.URL_LIST, "post", params=params, data={"classes": items}
        )

    def delete(self, project_id: int, annotation_class_id: int) -> ServiceResponse:
        return self.client.request(
            self.URL_GET.format(annotation_class_id),
            "delete",
            params={"project_id": project_id},
        )
