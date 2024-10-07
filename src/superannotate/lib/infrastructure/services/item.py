import time
from typing import Dict
from typing import List

from lib.core import entities
from lib.core.exceptions import AppException
from lib.core.exceptions import BackendError
from lib.core.serviceproviders import BaseItemService
from lib.core.types import Attachment
from lib.core.types import AttachmentMeta


class ItemService(BaseItemService):
    URL_GET = "image/{}"
    URL_ATTACH = "image/ext-create"
    URL_MOVE_MULTIPLE = "image/move"
    URL_SET_ANNOTATION_STATUSES = "image/updateAnnotationStatusBulk"
    URL_COPY_MULTIPLE = "images/copy-image-or-folders"
    URL_COPY_PROGRESS = "images/copy-image-progress"
    URL_DELETE_ITEMS = "image/delete/images"
    URL_SET_APPROVAL_STATUSES = "/items/bulk/change"

    def update(self, project: entities.ProjectEntity, item: entities.BaseItemEntity):
        return self.client.request(
            self.URL_GET.format(item.id),
            "put",
            data=item.dict(),
            params={"project_id": project.id},
        )

    def attach(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        attachments: List[Attachment],
        upload_state_code,
        meta: Dict[str, AttachmentMeta],
        annotation_status_code=None,
    ):
        data = {
            "project_id": project.id,
            "folder_id": folder.id,
            "team_id": project.team_id,
            "images": [i.dict() for i in attachments],
            "upload_state": upload_state_code,
            "meta": meta,
        }
        if annotation_status_code:
            data["annotation_status"] = annotation_status_code
        return self.client.request(self.URL_ATTACH, "post", data=data)

    def copy_multiple(
        self,
        project: entities.ProjectEntity,
        from_folder: entities.FolderEntity,
        to_folder: entities.FolderEntity,
        item_names: List[str],
        include_annotations: bool = False,
        include_pin: bool = False,
    ):
        """
        Returns poll id.
        """
        return self.client.request(
            self.URL_COPY_MULTIPLE,
            "post",
            params={"project_id": project.id},
            data={
                "is_folder_copy": False,
                "image_names": item_names,
                "destination_folder_id": to_folder.id,
                "source_folder_id": from_folder.id,
                "include_annotations": include_annotations,
                "keep_pin_status": include_pin,
            },
        )

    def await_copy(self, project: entities.ProjectEntity, poll_id: int, items_count):
        try:
            await_time = items_count * 0.3
            timeout_start = time.time()
            while time.time() < timeout_start + await_time:
                response = self.client.request(
                    self.URL_COPY_PROGRESS,
                    "get",
                    params={"project_id": project.id, "poll_id": poll_id},
                )
                if not response.ok:
                    return response
                done_count, skipped, _ = response.data
                if done_count + skipped == items_count:
                    break
                time.sleep(4)
        except (AppException, Exception) as e:
            raise BackendError(e)

    def move_multiple(
        self,
        project: entities.ProjectEntity,
        from_folder: entities.FolderEntity,
        to_folder: entities.FolderEntity,
        item_names: List[str],
    ):
        return self.client.request(
            self.URL_MOVE_MULTIPLE,
            "post",
            params={"project_id": project.id},
            data={
                "image_names": item_names,
                "destination_folder_id": to_folder.id,
                "source_folder_id": from_folder.id,
            },
        )

    def set_statuses(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_names: List[str],
        annotation_status: int,
    ):
        return self.client.request(
            self.URL_SET_ANNOTATION_STATUSES,
            "put",
            params={"project_id": project.id},
            data={
                "folder_id": folder.id,
                "annotation_status": annotation_status,
                "image_names": item_names,
            },
        )

    def set_approval_statuses(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_names: List[str],
        approval_status: int,
    ):
        return self.client.request(
            self.URL_SET_APPROVAL_STATUSES,
            "post",
            params={"project_id": project.id, "folder_id": folder.id},
            data={
                "item_names": item_names,
                "change_actions": {"APPROVAL_STATUS": approval_status},
            },
        )

    def delete_multiple(self, project: entities.ProjectEntity, item_ids: List[int]):
        return self.client.request(
            self.URL_DELETE_ITEMS,
            "put",
            params={"project_id": project.id},
            data={"image_ids": item_ids},
        )
