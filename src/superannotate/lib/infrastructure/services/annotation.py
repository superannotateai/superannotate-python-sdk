import asyncio
import copy
import io
import json
import logging
from pathlib import Path
from typing import Callable
from typing import Dict
from typing import List
from urllib.parse import urljoin

import aiohttp
import lib.core as constants
from lib.core import entities
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.service_types import UploadAnnotations
from lib.core.service_types import UploadAnnotationsResponse
from lib.core.serviceproviders import BaseAnnotationService
from lib.infrastructure.stream_data_handler import StreamedAnnotations

try:
    from pydantic.v1 import parse_obj_as
except ImportError:
    from pydantic import parse_obj_as

from superannotate.lib.infrastructure.services.http_client import AIOHttpSession

logger = logging.getLogger("sa")


class AnnotationService(BaseAnnotationService):
    ASSETS_PROVIDER_VERSION = "v3.01"
    DEFAULT_CHUNK_SIZE = 5000

    URL_GET_ANNOTATIONS = "items/annotations/download"
    URL_UPLOAD_ANNOTATIONS = "items/annotations/upload"
    URL_CLASSIFY_ITEM_SIZE = "items/annotations/download/method"
    URL_DOWNLOAD_LARGE_ANNOTATION = "items/{item_id}/annotations/download"
    URL_START_FILE_UPLOAD_PROCESS = "items/{item_id}/annotations/upload/multipart/start"
    URL_START_FILE_SEND_FINISH = "items/{item_id}/annotations/upload/multipart/finish"
    URL_START_FILE_SYNC_STATUS = "items/{item_id}/annotations/sync/status"
    URL_START_FILE_SYNC = "items/{item_id}/annotations/sync"
    URL_START_FILE_SEND_PART = "items/{item_id}/annotations/upload/multipart/part"
    URL_DELETE_ANNOTATIONS = "annotations/remove"
    URL_DELETE_ANNOTATIONS_PROGRESS = "annotations/getRemoveStatus"
    URL_ANNOTATION_SCHEMAS = "items/annotations/schema"

    @property
    def assets_provider_url(self):

        if self.client.api_url != constants.BACKEND_URL:
            return f"https://assets-provider.devsuperannotate.com/api/{self.ASSETS_PROVIDER_VERSION}/"
        return f"https://assets-provider.superannotate.com/api/{self.ASSETS_PROVIDER_VERSION}/"

    def get_schema(self, project_type: int, version: str):
        return self.client.request(
            urljoin(self.assets_provider_url, self.URL_ANNOTATION_SCHEMAS),
            "get",
            params={
                "project_type": project_type,
                "version": version,
            },
        )

    async def _sync_large_annotation(self, team_id, project_id, item_id):
        sync_params = {
            "team_id": team_id,
            "project_id": project_id,
            "desired_transform_version": "export",
            "desired_version": "V1.00",
            "current_transform_version": "V1.00",
            "current_source": "main",
            "desired_source": "secondary",
        }
        sync_url = urljoin(
            self.assets_provider_url,
            self.URL_START_FILE_SYNC.format(item_id=item_id),
        )
        async with AIOHttpSession(
            connector=aiohttp.TCPConnector(ssl=False),
            headers=self.client.default_headers,
            raise_for_status=True,
        ) as session:
            _response = await session.request("post", sync_url, params=sync_params)
            sync_params.pop("current_source")
            sync_params.pop("desired_source")

            synced = False
            sync_status_url = urljoin(
                self.assets_provider_url,
                self.URL_START_FILE_SYNC_STATUS.format(item_id=item_id),
            )
            while synced != "SUCCESS":
                synced = await session.get(sync_status_url, params=sync_params)
                synced = await synced.json()
                synced = synced["status"]
                await asyncio.sleep(5)
        return synced

    async def get_big_annotation(
        self,
        project: entities.ProjectEntity,
        item: entities.BaseItemEntity,
        reporter: Reporter,
    ) -> dict:
        url = urljoin(
            self.assets_provider_url,
            self.URL_DOWNLOAD_LARGE_ANNOTATION.format(item_id=item.id),
        )

        query_params = {
            "team_id": project.team_id,
            "project_id": project.id,
            "annotation_type": "MAIN",
            "version": "V1.00",
        }

        await self._sync_large_annotation(
            team_id=project.team_id, project_id=project.id, item_id=item.id
        )

        async with AIOHttpSession(
            connector=aiohttp.TCPConnector(ssl=False),
            headers=self.client.default_headers,
            raise_for_status=True,
        ) as session:
            start_response = await session.request("post", url, params=query_params)
            large_annotation = await start_response.json()

        reporter.update_progress()
        return large_annotation

    async def list_small_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_ids: List[int],
        reporter: Reporter,
        callback: Callable = None,
    ) -> List[dict]:
        query_params = {
            "team_id": project.team_id,
            "project_id": project.id,
            # "folder_id": folder.id,
        }

        handler = StreamedAnnotations(
            self.client.default_headers,
            reporter,
            map_function=lambda x: {"image_ids": x},
            callback=callback,
        )
        return await handler.list_annotations(
            method="post",
            url=urljoin(self.assets_provider_url, self.URL_GET_ANNOTATIONS),
            data=item_ids,
            params=query_params,
        )

    def get_upload_chunks(
        self,
        project: entities.ProjectEntity,
        item_ids: List[int],
    ) -> Dict[str, List]:
        response_data = {"small": [], "large": []}
        response = self.client.request(
            url=urljoin(self.assets_provider_url, self.URL_CLASSIFY_ITEM_SIZE),
            method="POST",
            params={"limit": len(item_ids)},
            data={"project_id": project.id, "item_ids": item_ids},
        )
        if not response.ok:
            raise AppException(response.error)
        response_data["small"] = [
            i["data"] for i in response.data.get("small", {}).values()
        ]
        response_data["large"] = response.data.get("large", [])
        return response_data

    async def download_big_annotation(
        self,
        project: entities.ProjectEntity,
        download_path: str,
        item: entities.BaseItemEntity,
        callback: Callable = None,
    ):
        item_id = item.id
        item_name = item.name
        query_params = {
            "team_id": project.team_id,
            "project_id": project.id,
            "annotation_type": "MAIN",
            "version": "V1.00",
        }

        url = urljoin(
            self.assets_provider_url,
            self.URL_DOWNLOAD_LARGE_ANNOTATION.format(item_id=item_id),
        )

        await self._sync_large_annotation(
            team_id=project.team_id, project_id=project.id, item_id=item_id
        )

        async with AIOHttpSession(
            connector=aiohttp.TCPConnector(ssl=False),
            headers=self.client.default_headers,
            raise_for_status=True,
        ) as session:
            start_response = await session.request("post", url, params=query_params)
            res = await start_response.json()
            Path(download_path).mkdir(exist_ok=True, parents=True)

            dest_path = Path(download_path) / (item_name + ".json")
            with open(dest_path, "w") as fp:
                if callback:
                    res = callback(res)
                json.dump(res, fp)

    async def download_small_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        reporter: Reporter,
        download_path: str,
        item_ids: List[int],
        callback: Callable = None,
    ):
        query_params = {
            "team_id": project.team_id,
            "project_id": project.id,
            "folder_id": folder.id,
        }
        handler = StreamedAnnotations(
            headers=self.client.default_headers,
            reporter=reporter,
            map_function=lambda x: {"image_ids": x},
            callback=callback,
        )

        return await handler.download_annotations(
            method="post",
            url=urljoin(self.assets_provider_url, self.URL_GET_ANNOTATIONS),
            data=item_ids,
            params=query_params,
            download_path=download_path,
        )

    async def upload_small_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items_name_data_map: Dict[str, dict],
    ) -> UploadAnnotationsResponse:
        params = [
            ("team_id", project.team_id),
            ("project_id", project.id),
            ("folder_id", folder.id),
            *[("image_names[]", item_name) for item_name in items_name_data_map.keys()],
        ]
        url = urljoin(self.assets_provider_url, f"{self.URL_UPLOAD_ANNOTATIONS}")
        headers = copy.copy(self.client.default_headers)
        del headers["Content-Type"]
        async with AIOHttpSession(
            headers=headers,
            connector=aiohttp.TCPConnector(ssl=False),
        ) as session:
            form_data = aiohttp.FormData(
                quote_fields=False,
            )
            tmp = {}
            for name, data in items_name_data_map.items():
                tmp[name] = io.StringIO()
                json.dump({"data": data}, tmp[name], allow_nan=False)
                tmp[name].seek(0)

            for key, data in tmp.items():
                form_data.add_field(
                    key,
                    data,
                    filename=key,
                    content_type="application/json",
                )
            _response = await session.request(
                "post", url, params=params, data=form_data
            )
            if not _response.ok:
                logger.debug(f"Status code {str(_response.status)}")
                logger.debug(await _response.text())
                raise AppException("Can't upload annotations.")
            data_json = await _response.json()
            response = UploadAnnotationsResponse()
            response.status = _response.status
            response._content = await _response.text()
            #  TODO add error handling
            response.res_data = parse_obj_as(UploadAnnotations, data_json)
            return response

    async def upload_big_annotation(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_id: int,
        data: io.StringIO,
        chunk_size: int,
    ) -> bool:
        async with AIOHttpSession(
            connector=aiohttp.TCPConnector(ssl=False),
            headers=self.client.default_headers,
        ) as session:
            params = {
                "team_id": project.team_id,
                "project_id": project.id,
                "folder_id": folder.id,
            }
            url = urljoin(
                self.assets_provider_url,
                self.URL_START_FILE_UPLOAD_PROCESS.format(item_id=item_id),
            )
            start_response = await session.request("post", url, params=params)
            if not start_response.ok:
                raise AppException(str(await start_response.text()))
            process_info = await start_response.json()
            params["path"] = process_info["path"]
            headers = copy.copy(self.client.default_headers)
            headers["upload_id"] = process_info["upload_id"]
            chunk_id = 1
            data_sent = False
            while True:
                chunk = data.read(chunk_size)
                params["chunk_id"] = chunk_id
                if chunk:
                    data_sent = True
                    response = await session.request(
                        "post",
                        urljoin(
                            self.assets_provider_url,
                            self.URL_START_FILE_SEND_PART.format(item_id=item_id),
                        ),
                        params=params,
                        headers=headers,
                        data=json.dumps({"data_chunk": chunk}, allow_nan=False),
                    )
                    if not response.ok:
                        raise AppException(str(await response.text()))
                    chunk_id += 1
                if not chunk and not data_sent:
                    return False
                if len(chunk) < chunk_size:
                    break
            del params["chunk_id"]
            response = await session.request(
                "post",
                urljoin(
                    self.assets_provider_url,
                    self.URL_START_FILE_SEND_FINISH.format(item_id=item_id),
                ),
                headers=headers,
                params=params,
            )
            if not response.ok:
                raise AppException(str(await response.text()))
            del params["path"]
            response = await session.request(
                "post",
                urljoin(
                    self.assets_provider_url,
                    self.URL_START_FILE_SYNC.format(item_id=item_id),
                ),
                params=params,
                headers=headers,
            )
            if not response.ok:
                raise AppException(str(await response.text()))
            while True:
                response = await session.request(
                    "get",
                    urljoin(
                        self.assets_provider_url,
                        self.URL_START_FILE_SYNC_STATUS.format(item_id=item_id),
                    ),
                    params=params,
                    headers=headers,
                )
                if response.ok:
                    data = await response.json()
                    status = data.get("status")
                    if status == "SUCCESS":
                        return True
                    elif status.startswith("FAILED"):
                        return False
                    await asyncio.sleep(15)
                else:
                    raise AppException(str(await response.text()))

    def delete(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity = None,
        item_names: List[str] = None,
    ):
        data = {}
        params = {"project_id": project.id}
        if folder:
            params["folder_id"] = folder.id
        if item_names:
            data["image_names"] = item_names
        return self.client.request(
            self.URL_DELETE_ANNOTATIONS, "post", params=params, data=data
        )

    def get_delete_progress(self, project: entities.ProjectEntity, poll_id: int):
        return self.client.request(
            self.URL_DELETE_ANNOTATIONS_PROGRESS,
            "get",
            params={"project_id": project.id, "poll_id": poll_id},
        )
