import time
from typing import Dict
from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.exceptions import BackendError
from lib.core.service_types import ClassificationResponse
from lib.core.service_types import DocumentResponse
from lib.core.service_types import ImageResponse
from lib.core.service_types import ItemListResponse
from lib.core.service_types import PointCloudResponse
from lib.core.service_types import TiledResponse
from lib.core.service_types import VideoResponse
from lib.core.serviceproviders import BaseItemService
from lib.core.types import Attachment
from lib.core.types import AttachmentMeta


class ItemService(BaseItemService):
    URL_LIST = "items"
    URL_GET = "image/{}"
    URL_LIST_BY_NAMES = "images/getBulk"
    URL_ATTACH = "image/ext-create"
    URL_MOVE_MULTIPLE = "image/move"
    URL_COPY_MULTIPLE = "images/copy-image-or-folders"
    URL_COPY_PROGRESS = "images/copy-image-progress"
    URL_DELETE_ITEMS = "image/delete/images"
    URL_SET_ANNOTATION_STATUSES = "image/updateAnnotationStatusBulk"
    URL_GET_BY_ID = "image/{image_id}"

    PROJECT_TYPE_RESPONSE_MAP = {
        ProjectType.VECTOR: ImageResponse,
        ProjectType.OTHER: ClassificationResponse,
        ProjectType.VIDEO: VideoResponse,
        ProjectType.TILED: TiledResponse,
        ProjectType.PIXEL: ImageResponse,
        ProjectType.DOCUMENT: DocumentResponse,
        ProjectType.POINT_CLOUD: PointCloudResponse,
    }

    def get_by_id(self, item_id, project_id, project_type):

        params = {"project_id": project_id}

        content_type = self.PROJECT_TYPE_RESPONSE_MAP[project_type]

        response = self.client.request(
            url=self.URL_GET_BY_ID.format(image_id=item_id),
            params=params,
            content_type=content_type,
        )

        return response

    def list(self, condition: Condition = None):
        return self.client.paginate(
            url=f"{self.URL_LIST}?{condition.build_query()}"
            if condition
            else self.URL_LIST,
            chunk_size=2000,
            item_type=entities.BaseItemEntity,
        )

    def update(self, project: entities.ProjectEntity, item: entities.BaseItemEntity):
        return self.client.request(
            self.URL_GET.format(item.id),
            "put",
            data=item.dict(),
            params={"project_id": project.id},
        )

    def list_by_names(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        names: List[str],
    ):
        chunk_size = 200
        items = []
        response = None
        for i in range(0, len(names), chunk_size):
            response = self.client.request(
                self.URL_LIST_BY_NAMES,
                "post",
                data={
                    "project_id": project.id,
                    "team_id": project.team_id,
                    "folder_id": folder.id,
                    "names": names[i : i + chunk_size],  # noqa
                },
                content_type=ItemListResponse,
            )
            if not response.ok:
                return response
            items.extend(response.data)
        response.data = items
        return response

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

    def delete_multiple(self, project: entities.ProjectEntity, item_ids: List[int]):
        return self.client.request(
            self.URL_DELETE_ITEMS,
            "put",
            params={"project_id": project.id},
            data={"image_ids": item_ids},
        )
