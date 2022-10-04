from typing import Dict
from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.serviceproviders import BaseItemService
from lib.core.types import Attachment
from lib.core.types import AttachmentMeta


class ItemService(BaseItemService):
    URL_LIST = "items"
    URL_LIST_BY_NAME = "images/getBulk"
    URL_ATTACH = "image/ext-create"

    def list(self, condition: Condition = None):
        return self.client.paginate(
            url=f"{self.URL_LIST}?{condition.build_query()}"
            if condition
            else self.URL_LIST,
            chunk_size=2000,
            item_type=entities.BaseItemEntity,
        )

    def list_by_names(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        names: List[str],
    ):
        return self.client.request(
            self.URL_LIST_BY_NAME,
            "post",
            data={
                "project_id": project.id,
                "team_id": project.team_id,
                "folder_id": folder.id,
                "names": names,
            },
        )

    def attach(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        attachments: List[Attachment],
        annotation_status_code,
        upload_state_code,
        meta: Dict[str, AttachmentMeta],
    ):
        data = {
            "project_id": project.id,
            "folder_id": folder.id,
            "team_id": project.team_id,
            "images": [i.dict() for i in attachments],
            "annotation_status": annotation_status_code,
            "upload_state": upload_state_code,
            "meta": meta,
        }
        return self.client.request(self.URL_ATTACH, "post", data=data)
