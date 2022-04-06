import asyncio
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple
from typing import Union
from urllib.parse import urljoin

import lib.core as constance
import requests.packages.urllib3
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.service_types import DownloadMLModelAuthData
from lib.core.service_types import ServiceResponse
from lib.core.service_types import UploadAnnotationAuthData
from lib.core.service_types import UserLimits
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.infrastructure.helpers import timed_lru_cache
from lib.infrastructure.stream_data_handler import StreamedAnnotations
from requests.exceptions import HTTPError


requests.packages.urllib3.disable_warnings()


class PydanticEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "deserialize"):
            return obj.deserialize()
        return json.JSONEncoder.default(self, obj)


class BaseBackendService(SuperannotateServiceProvider):
    AUTH_TYPE = "sdk"
    PAGINATE_BY = 100
    LIMIT = 100
    MAX_ITEMS_COUNT = 50 * 1000

    """
    Base service class
    """

    def __init__(
        self,
        api_url: str,
        auth_token: str,
        logger,
        paginate_by=None,
        verify_ssl=False,
        testing: bool = False,
    ):
        self.api_url = api_url
        self._auth_token = auth_token
        self.logger = logger
        self._paginate_by = paginate_by
        self._verify_ssl = verify_ssl
        self.team_id = auth_token.split("=")[-1]
        self._testing = testing
        self.get_session()

    @property
    def assets_provider_url(self):
        if self.api_url != constance.BACKEND_URL:
            return "https://assets-provider.devsuperannotate.com/api/v1/"
        return "https://assets-provider.superannotate.com/api/v1/"

    @timed_lru_cache(seconds=360)
    def get_session(self):
        session = requests.Session()
        session.headers.update(self.default_headers)
        return session

    @property
    def default_headers(self):
        return {
            "Authorization": self._auth_token,
            "authtype": self.AUTH_TYPE,
            "Content-Type": "application/json",
            # "User-Agent": constance.__version__,
        }

    @property
    def safe_api(self):
        """
        Context manager which will handle requests calls.
        """

        @contextmanager
        def safe_api():
            """
            Context manager which handles Requests error.
            """
            try:
                yield None
            except (HTTPError, ConnectionError) as exc:
                raise AppException(f"Unknown exception: {exc}.")

        return safe_api

    @property
    def paginate_by(self):
        if self._paginate_by:
            return self._paginate_by
        else:
            return self.PAGINATE_BY

    def _request(
        self,
        url,
        method="get",
        data=None,
        headers=None,
        params=None,
        retried=0,
        content_type=None,
    ) -> Union[requests.Response, ServiceResponse]:
        kwargs = {"data": json.dumps(data, cls=PydanticEncoder)} if data else {}
        session = self.get_session()
        session.headers.update(headers if headers else {})
        with self.safe_api():
            req = requests.Request(method=method, url=url, **kwargs, params=params)
            prepared = session.prepare_request(req)
            response = session.send(request=prepared, verify=self._verify_ssl)
        if response.status_code == 404 and retried < 3:
            return self._request(
                url,
                method="get",
                data=None,
                headers=None,
                params=None,
                retried=retried + 1,
                content_type=content_type,
            )
        if response.status_code > 299:
            self.logger.error(
                f"Got {response.status_code} response from backend: {response.text}"
            )
        if content_type:
            return ServiceResponse(response, content_type)
        return response

    def _get_page(self, url, offset, params=None, key_field: str = None):
        splitter = "&" if "?" in url else "?"
        url = f"{url}{splitter}offset={offset}"

        response = self._request(url, params=params)
        if response.status_code != 200:
            return {"data": []}, 0
            # raise AppException(f"Got invalid response for url {url}: {response.text}.")
        data = response.json()
        if data:
            if isinstance(data, dict):
                if key_field:
                    data = data[key_field]
                if data.get("count", 0) < self.LIMIT:
                    return data, 0
                else:
                    return data, data.get("count", 0) - offset
            if isinstance(data, list):
                return {"data": data}, 0
        return {"data": []}, 0

    def _get_all_pages(self, url, offset=0, params=None, key_field: str = None):
        total = list()

        while True:
            resources, remains_count = self._get_page(url, offset, params, key_field)
            total.extend(resources["data"])
            if remains_count <= 0:
                break
            offset += len(resources["data"])
        return total


class SuperannotateBackendService(BaseBackendService):
    """
    Manage projects, images and team in the Superannotate
    """

    DEFAULT_CHUNK_SIZE = 1000

    URL_USERS = "users"
    URL_LIST_PROJECTS = "projects"
    URL_FOLDERS_IMAGES = "images-folders"
    URL_CREATE_PROJECT = "project"
    URL_GET_PROJECT = "project/{}"
    URL_GET_FOLDER_BY_NAME = "folder/getFolderByName"
    URL_CREATE_FOLDER = "folder"
    URL_UPDATE_FOLDER = "folder/{}"
    URL_GET_IMAGE = "image/{}"
    URL_GET_IMAGES = "images"
    URL_GET_ITEMS = "items"
    URL_BULK_GET_IMAGES = "images/getBulk"
    URL_DELETE_FOLDERS = "image/delete/images"
    URL_CREATE_IMAGE = "image/ext-create"
    URL_PROJECT_SETTINGS = "project/{}/settings"
    URL_PROJECT_WORKFLOW = "project/{}/workflow"
    URL_SHARE_PROJECT = "project/{}/share"
    URL_SHARE_PROJECT_BULK = "project/{}/share/bulk"
    URL_ANNOTATION_CLASSES = "classes"
    URL_TEAM = "team"
    URL_INVITE_CONTRIBUTOR = "team/{}/invite"
    URL_INVITE_CONTRIBUTORS = "team/{}/inviteUsers"
    URL_PREPARE_EXPORT = "export"
    URL_COPY_IMAGES_FROM_FOLDER = "images/copy-image-or-folders"
    URL_MOVE_IMAGES_FROM_FOLDER = "image/move"
    URL_GET_COPY_PROGRESS = "images/copy-image-progress"
    URL_ASSIGN_IMAGES = "images/editAssignment/"
    URL_ASSIGN_FOLDER = "folder/editAssignment"
    URL_S3_ACCESS_POINT = "/project/{}/get-image-s3-access-point"
    URL_S3_UPLOAD_STATUS = "/project/{}/getS3UploadStatus"
    URL_GET_EXPORTS = "exports"
    URL_GET_CLASS = "class/{}"
    URL_ANNOTATION_UPLOAD_PATH_TOKEN = "images/getAnnotationsPathsAndTokens"
    URL_PRE_ANNOTATION_UPLOAD_PATH_TOKEN = "images/getPreAnnotationsPathsAndTokens"
    URL_GET_TEMPLATES = "templates"
    URL_PROJECT_WORKFLOW_ATTRIBUTE = "project/{}/workflow_attribute"
    URL_MODELS = "ml_models"
    URL_MODEL = "ml_model"
    URL_GET_MODEL_METRICS = "ml_models/{}/getCurrentMetrics"
    URL_BULK_GET_FOLDERS = "foldersByTeam"
    URL_GET_EXPORT = "export/{}"
    URL_GET_ML_MODEL_DOWNLOAD_TOKEN = "ml_model/getMyModelDownloadToken/{}"
    URL_PREDICTION = "images/prediction"
    URL_SET_IMAGES_STATUSES_BULK = "image/updateAnnotationStatusBulk"
    URL_DELETE_ANNOTATIONS = "annotations/remove"
    URL_DELETE_ANNOTATIONS_PROGRESS = "annotations/getRemoveStatus"
    URL_GET_LIMITS = "project/{}/limitationDetails"
    URL_GET_ANNOTATIONS = "images/annotations/stream"
    URL_UPLOAD_PRIORITY_SCORES = "images/updateEntropy"
    URL_GET_INTEGRATIONS = "integrations"
    URL_ATTACH_INTEGRATIONS = "image/integration/create"
    URL_SAQUL_QUERY = "/images/search/advanced"
    URL_VALIDATE_SAQUL_QUERY = "/images/parse/query/advanced"

    def upload_priority_scores(
        self, team_id: int, project_id: int, folder_id: int, priorities: list
    ) -> dict:
        upload_priority_score_url = urljoin(
            self.api_url, self.URL_UPLOAD_PRIORITY_SCORES
        )
        res = self._request(
            upload_priority_score_url,
            "post",
            params={
                "team_id": team_id,
                "project_id": project_id,
                "folder_id": folder_id,
            },
            data={"image_entropies": priorities},
        )
        return res.json()

    def get_project(self, uuid: int, team_id: int):
        get_project_url = urljoin(self.api_url, self.URL_GET_PROJECT.format(uuid))
        res = self._request(get_project_url, "get", params={"team_id": team_id})
        return res.json()

    def get_s3_upload_auth_token(self, team_id: int, folder_id: int, project_id: int):
        auth_token_url = urljoin(
            self.api_url,
            self.URL_GET_PROJECT.format(project_id) + "/sdkImageUploadToken",
        )
        response = self._request(
            auth_token_url, "get", params={"team_id": team_id, "folder_id": folder_id}
        )
        return response.json()

    def get_download_token(
        self,
        project_id: int,
        team_id: int,
        folder_id: int,
        image_id: int,
        include_original: int = 1,
    ):
        download_token_url = urljoin(
            self.api_url,
            self.URL_GET_IMAGE.format(image_id)
            + "/annotation/getAnnotationDownloadToken",
        )
        response = self._request(
            download_token_url,
            "get",
            params={
                "project_id": project_id,
                "team_id": team_id,
                "folder_id": folder_id,
                "include_original": include_original,
            },
        )
        return response.json()

    def get_upload_token(
        self, project_id: int, team_id: int, folder_id: int, image_id: int,
    ):
        download_token_url = urljoin(
            self.api_url,
            self.URL_GET_IMAGE.format(image_id)
            + "/annotation/getAnnotationUploadToken",
        )
        response = self._request(
            download_token_url,
            "get",
            params={
                "project_id": project_id,
                "team_id": team_id,
                "folder_id": folder_id,
            },
        )
        return response.json()

    def get_projects(self, query_string: str = None) -> list:
        url = urljoin(self.api_url, self.URL_LIST_PROJECTS)
        if query_string:
            url = f"{url}?{query_string}"
        data = self._get_all_pages(url)
        return data

    def create_project(self, project_data: dict) -> dict:
        create_project_url = urljoin(self.api_url, self.URL_CREATE_PROJECT)
        res = self._request(create_project_url, "post", project_data)
        return res.json()

    def delete_project(self, uuid: int, query_string: str = None) -> bool:
        url = urljoin(self.api_url, self.URL_GET_PROJECT.format(uuid))
        if query_string:
            url = f"{url}?{query_string}"
        res = self._request(url, "delete")
        return res.ok

    def update_project(self, data: dict, query_string: str = None) -> dict:
        url = urljoin(self.api_url, self.URL_GET_PROJECT.format(data["id"]))
        if query_string:
            url = f"{url}?{query_string}"
        res = self._request(url, "put", data)
        return res.json()

    def attach_files(
        self,
        project_id: int,
        folder_id: int,
        team_id: int,
        files: List[Dict],
        annotation_status_code,
        upload_state_code,
        meta,
    ):
        data = {
            "project_id": project_id,
            "folder_id": folder_id,
            "team_id": team_id,
            "images": files,
            "annotation_status": annotation_status_code,
            "upload_state": upload_state_code,
            "meta": meta,
        }
        create_image_url = urljoin(self.api_url, self.URL_CREATE_IMAGE)
        response = self._request(create_image_url, "post", data)
        return response.json()

    def get_folder(self, query_string: str):
        get_folder_url = urljoin(self.api_url, self.URL_GET_FOLDER_BY_NAME)
        if query_string:
            get_folder_url = f"{get_folder_url}?{query_string}"
        response = self._request(get_folder_url, "get")
        if response.ok:
            return response.json()

    def get_folders(self, query_string: str = None, params: dict = None):
        get_folder_url = urljoin(self.api_url, self.URL_FOLDERS_IMAGES)
        if query_string:
            get_folder_url = f"{get_folder_url}?{query_string}"
        return self._get_all_pages(get_folder_url, params=params, key_field="folders")

    def delete_folders(self, project_id: int, team_id: int, folder_ids: List[int]):
        delete_folders_url = urljoin(self.api_url, self.URL_DELETE_FOLDERS)
        params = {"team_id": team_id, "project_id": project_id}
        response = self._request(
            delete_folders_url, "put", params=params, data={"folder_ids": folder_ids}
        )
        return response.ok

    def create_folder(self, project_id: int, team_id: int, folder_name: str):
        create_folder_url = urljoin(self.api_url, self.URL_CREATE_FOLDER)
        data = {"name": folder_name}
        params = {"project_id": project_id, "team_id": team_id}
        res = self._request(create_folder_url, "post", data=data, params=params)
        return res.json()

    def update_folder(self, project_id: int, team_id: int, folder_data: dict):
        update_folder_url = urljoin(
            self.api_url, self.URL_UPDATE_FOLDER.format(folder_data["id"])
        )
        params = {"project_id": project_id, "team_id": team_id}
        res = self._request(update_folder_url, "put", data=folder_data, params=params)
        if res.ok:
            return res.json()

    def get_project_settings(self, project_id: int, team_id: int):
        get_settings_url = urljoin(
            self.api_url, self.URL_PROJECT_SETTINGS.format(project_id)
        )
        res = self._request(get_settings_url, "get", params={"team_id": team_id})
        return res.json()

    def set_project_settings(self, project_id: int, team_id: int, data: List):
        set_project_settings_url = urljoin(
            self.api_url, self.URL_PROJECT_SETTINGS.format(project_id)
        )
        res = self._request(
            set_project_settings_url,
            "put",
            data={"settings": data},
            params={"team_id": team_id},
        )
        return res.json()

    def get_annotation_classes(
        self, project_id: int, team_id: int, query_string: str = None
    ):
        get_annotation_classes_url = urljoin(self.api_url, self.URL_ANNOTATION_CLASSES)
        if query_string:
            get_annotation_classes_url = f"{get_annotation_classes_url}?{query_string}"
        params = {"project_id": project_id, "team_id": team_id}
        return self._get_all_pages(get_annotation_classes_url, params=params)

    def set_annotation_classes(self, project_id: int, team_id: int, data: List):
        set_annotation_class_url = urljoin(self.api_url, self.URL_ANNOTATION_CLASSES)
        params = {
            "team_id": team_id,
            "project_id": project_id,
        }
        res = self._request(
            set_annotation_class_url, "post", params=params, data={"classes": data}
        )
        return res.json()

    def get_project_workflows(self, project_id: int, team_id: int):
        get_project_workflow_url = urljoin(
            self.api_url, self.URL_PROJECT_WORKFLOW.format(project_id)
        )
        return self._get_all_pages(
            get_project_workflow_url, params={"team_id": team_id}
        )

    def set_project_workflow(self, project_id: int, team_id: int, data: Dict):
        set_project_workflow_url = urljoin(
            self.api_url, self.URL_PROJECT_WORKFLOW.format(project_id)
        )
        res = self._request(
            set_project_workflow_url,
            "post",
            data={"steps": [data]},
            params={"team_id": team_id},
        )
        return res.json()

    def set_project_workflow_bulk(self, project_id: int, team_id: int, steps: list):
        set_project_workflow_url = urljoin(
            self.api_url, self.URL_PROJECT_WORKFLOW.format(project_id)
        )
        res = self._request(
            set_project_workflow_url,
            "post",
            data={"steps": steps},
            params={"team_id": team_id},
        )
        return res.json()

    def share_project_bulk(self, project_id: int, team_id: int, users: list):
        share_project_url = urljoin(
            self.api_url, self.URL_SHARE_PROJECT_BULK.format(project_id)
        )
        res = self._request(
            share_project_url,
            "post",
            data={"users": users},
            params={"team_id": team_id},
        )
        return res.json()

    def search_team_contributors(self, team_id: int, query_string: str = None):

        list_users_url = urljoin(self.api_url, self.URL_USERS)
        if query_string:
            list_users_url = f"{list_users_url}?{query_string}"
        params = {"team_id": team_id}
        return self._get_all_pages(list_users_url, params=params)

    def un_share_project(self, project_id: int, team_id: int, user_id: int):
        users_url = urljoin(self.api_url, self.URL_SHARE_PROJECT.format(project_id))

        res = self._request(
            users_url, "delete", data={"user_id": user_id}, params={"team_id": team_id}
        )
        return res.ok

    def get_images(self, query_string: str = None):
        url = urljoin(self.api_url, self.URL_FOLDERS_IMAGES)
        if query_string:
            url = f"{url}?{query_string}"
        pages = self._get_all_pages(url, key_field="images")
        return [image for image in pages]

    def list_images(self, query_string):
        url = urljoin(self.api_url, self.URL_GET_IMAGES)
        if query_string:
            url = f"{url}?{query_string}"
        return self._get_all_pages(url)

    def list_items(self, query_string) -> List[dict]:
        url = urljoin(self.api_url, self.URL_GET_ITEMS)
        if query_string:
            url = f"{url}?{query_string}"
        return self._get_all_pages(url)

    def prepare_export(
        self,
        project_id: int,
        team_id: int,
        folders: List[str],
        annotation_statuses: Iterable[str],
        include_fuse: bool,
        only_pinned: bool,
    ):
        prepare_export_url = urljoin(self.api_url, self.URL_PREPARE_EXPORT)

        annotation_statuses = ",".join(
            [str(constance.AnnotationStatus.get_value(i)) for i in annotation_statuses]
        )

        data = {
            "include": annotation_statuses,
            "fuse": int(include_fuse),
            "is_pinned": int(only_pinned),
            "coco": 0,
            "time": datetime.now().strftime("%b %d %Y %H:%M"),
        }
        if folders:
            data["folder_names"] = folders

        res = self._request(
            prepare_export_url,
            "post",
            data=data,
            params={"project_id": project_id, "team_id": team_id},
        )
        return res.json()

    def get_team(self, team_id: int):
        get_team_url = urljoin(self.api_url, f"{self.URL_TEAM}/{team_id}")
        res = self._request(get_team_url, "get")
        return res.json()

    def delete_team_invitation(self, team_id: int, token: str, email: str) -> bool:
        invite_contributor_url = urljoin(
            self.api_url, self.URL_INVITE_CONTRIBUTOR.format(team_id)
        )
        res = self._request(
            invite_contributor_url, "delete", data={"token": token, "e_mail": email}
        )
        return res.ok

    def invite_contributors(
        self, team_id: int, team_role: int, emails: list
    ) -> Tuple[List[str], List[str]]:
        invite_contributors_url = urljoin(
            self.api_url, self.URL_INVITE_CONTRIBUTORS.format(team_id)
        )
        res = self._request(
            invite_contributors_url,
            "post",
            data=dict(emails=emails, team_role=team_role),
        ).json()
        return res["success"]["emails"], res["failed"]["emails"]

    def update_image(self, image_id: int, team_id: int, project_id: int, data: dict):
        update_image_url = urljoin(self.api_url, self.URL_GET_IMAGE.format(image_id))

        res = self._request(
            update_image_url,
            "put",
            data=data,
            params={"team_id": team_id, "project_id": project_id},
        )
        return res.ok

    def copy_images_between_folders_transaction(
        self,
        team_id: int,
        project_id: int,
        from_folder_id: int,
        to_folder_id: int,
        images: List[str],
        include_annotations: bool = False,
        include_pin: bool = False,
    ) -> int:
        """
        Returns poll id.
        """
        copy_images_url = urljoin(self.api_url, self.URL_COPY_IMAGES_FROM_FOLDER)
        res = self._request(
            copy_images_url,
            "post",
            params={"team_id": team_id, "project_id": project_id},
            data={
                "is_folder_copy": False,
                "image_names": images,
                "destination_folder_id": to_folder_id,
                "source_folder_id": from_folder_id,
                "include_annotations": include_annotations,
                "keep_pin_status": include_pin,
            },
        )
        if res.ok:
            return res.json()["poll_id"]

    def move_images_between_folders(
        self,
        team_id: int,
        project_id: int,
        from_folder_id: int,
        to_folder_id: int,
        images: List[str],
    ) -> List[str]:
        move_images_url = urljoin(self.api_url, self.URL_MOVE_IMAGES_FROM_FOLDER)
        res = self._request(
            move_images_url,
            "post",
            params={"team_id": team_id, "project_id": project_id},
            data={
                "image_names": images,
                "destination_folder_id": to_folder_id,
                "source_folder_id": from_folder_id,
            },
        )
        if res.ok:
            return res.json()["done"]
        return []

    def get_progress(
        self, project_id: int, team_id: int, poll_id: int
    ) -> Tuple[int, int]:
        get_progress_url = urljoin(self.api_url, self.URL_GET_COPY_PROGRESS)

        res = self._request(
            get_progress_url,
            "get",
            params={"team_id": team_id, "project_id": project_id, "poll_id": poll_id},
        ).json()
        return res["done"], res["skipped"]

    def get_duplicated_images(
        self, project_id: int, team_id: int, folder_id: int, images: List[str]
    ) -> List[str]:
        get_duplications_url = urljoin(self.api_url, self.URL_BULK_GET_IMAGES)

        res = self._request(
            get_duplications_url,
            "post",
            data={
                "project_id": project_id,
                "team_id": team_id,
                "folder_id": folder_id,
                "names": images,
            },
        )
        return res.json()

    def delete_image(self, image_id, team_id: int, project_id: int):
        delete_image_url = urljoin(self.api_url, self.URL_GET_IMAGE.format(image_id))

        res = self._request(
            delete_image_url,
            "delete",
            params={"team_id": team_id, "project_id": project_id},
        )
        return res.ok

    def set_images_statuses_bulk(
        self,
        image_names: list,
        team_id: int,
        project_id: int,
        folder_id: int,
        annotation_status: int,
    ):
        set_images_statuses_bulk_url = urljoin(
            self.api_url, self.URL_SET_IMAGES_STATUSES_BULK
        )

        res = self._request(
            set_images_statuses_bulk_url,
            "put",
            params={"team_id": team_id, "project_id": project_id},
            data={
                "folder_id": folder_id,
                "annotation_status": annotation_status,
                "image_names": image_names,
            },
        )
        return res.ok

    def get_bulk_images(
        self, project_id: int, team_id: int, folder_id: int, images: List[str]
    ) -> List[dict]:
        bulk_get_images_url = urljoin(self.api_url, self.URL_BULK_GET_IMAGES)
        res = self._request(
            bulk_get_images_url,
            "post",
            data={
                "project_id": project_id,
                "team_id": team_id,
                "folder_id": folder_id,
                "names": images,
            },
        )
        return res.json()

    def delete_images(self, project_id: int, team_id: int, image_ids: List[int]):
        delete_images_url = urljoin(self.api_url, self.URL_DELETE_FOLDERS)
        res = self._request(
            delete_images_url,
            "put",
            params={"team_id": team_id, "project_id": project_id},
            data={"image_ids": image_ids},
        )
        return res.json()

    def assign_images(
        self,
        team_id: int,
        project_id: int,
        folder_name: str,
        user: str,
        image_names: list,
    ):
        assign_images_url = urljoin(self.api_url, self.URL_ASSIGN_IMAGES)
        res = self._request(
            assign_images_url,
            "put",
            params={"team_id": team_id, "project_id": project_id},
            data={
                "image_names": image_names,
                "assign_user_id": user,
                "folder_name": folder_name,
            },
        )
        return res.ok

    def un_assign_images(
        self, team_id: int, project_id: int, folder_name: str, image_names: List[str],
    ):
        un_assign_images_url = urljoin(self.api_url, self.URL_ASSIGN_IMAGES)
        res = self._request(
            un_assign_images_url,
            "put",
            params={"team_id": team_id, "project_id": project_id},
            data={
                "image_names": image_names,
                "remove_user_ids": ["all"],
                "folder_name": folder_name,
            },
        )
        return res.ok

    def un_assign_folder(
        self, team_id: int, project_id: int, folder_name: str,
    ):
        un_assign_folder_url = urljoin(self.api_url, self.URL_ASSIGN_FOLDER)
        res = self._request(
            un_assign_folder_url,
            "post",
            params={"team_id": team_id, "project_id": project_id},
            data={"folder_name": folder_name, "remove_user_ids": ["all"]},
        )
        return res.ok

    def assign_folder(
        self, team_id: int, project_id: int, folder_name: str, users: list
    ):
        assign_folder_url = urljoin(self.api_url, self.URL_ASSIGN_FOLDER)
        res = self._request(
            assign_folder_url,
            "post",
            params={"team_id": team_id, "project_id": project_id},
            data={"folder_name": folder_name, "assign_user_ids": users},
        )
        return res.ok

    def get_exports(self, team_id: int, project_id: int):
        exports_url = urljoin(self.api_url, self.URL_GET_EXPORTS)
        res = self._request(
            exports_url, "get", params={"team_id": team_id, "project_id": project_id}
        )
        return res.json()

    def get_export(self, team_id: int, project_id: int, export_id: int):
        exports_url = urljoin(self.api_url, self.URL_GET_EXPORT.format(export_id))
        res = self._request(
            exports_url, "get", params={"team_id": team_id, "project_id": project_id}
        )
        return res.json()

    def upload_form_s3(
        self,
        project_id: int,
        team_id: int,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        from_folder_name: str,
        to_folder_id: int,
    ):
        upload_from_s3_url = urljoin(
            self.api_url, self.URL_S3_ACCESS_POINT.format(project_id)
        )
        response = self._request(
            upload_from_s3_url,
            "post",
            params={"team_id": team_id},
            data={
                "accessKeyID": access_key,
                "secretAccessKey": secret_key,
                "bucketName": bucket_name,
                "folderName": from_folder_name,
                "folder_id": to_folder_id,
            },
        )
        return response

    def get_upload_status(self, project_id: int, team_id: int, folder_id: int):
        get_upload_status_url = urljoin(
            self.api_url, self.URL_S3_UPLOAD_STATUS.format(project_id)
        )
        res = self._request(
            get_upload_status_url,
            "get",
            params={"team_id": team_id, "folder_id": folder_id},
        )
        return res.json().get("progress")

    def get_project_images_count(self, team_id: int, project_id: int):
        get_images_count_url = urljoin(self.api_url, self.URL_FOLDERS_IMAGES)
        res = self._request(
            get_images_count_url,
            "get",
            params={"team_id": team_id, "project_id": project_id},
        )
        return res.json()

    def delete_annotation_class(
        self, team_id: int, project_id: int, annotation_class_id: int
    ):
        delete_image_url = urljoin(
            self.api_url, self.URL_GET_CLASS.format(annotation_class_id)
        )
        res = self._request(
            delete_image_url,
            "delete",
            params={"team_id": team_id, "project_id": project_id},
        )
        return res.json()

    def set_project_workflow_attributes_bulk(
        self, project_id: int, team_id: int, attributes: list
    ):
        set_project_workflow_attribute_url = urljoin(
            self.api_url, self.URL_PROJECT_WORKFLOW_ATTRIBUTE.format(project_id)
        )
        res = self._request(
            set_project_workflow_attribute_url,
            "post",
            data={"data": attributes},
            params={"team_id": team_id},
        )
        return res.json()

    def get_annotation_upload_data(
        self, project_id: int, team_id: int, image_ids: List[int], folder_id: int
    ):
        get_annotation_upload_data_url = urljoin(
            self.api_url, self.URL_ANNOTATION_UPLOAD_PATH_TOKEN
        )
        response = self._request(
            get_annotation_upload_data_url,
            "post",
            data={
                "project_id": project_id,
                "team_id": team_id,
                "ids": image_ids,
                "folder_id": folder_id,
            },
            content_type=UploadAnnotationAuthData,
        )
        return response

    def get_pre_annotation_upload_data(
        self, project_id: int, team_id: int, image_ids: List[int], folder_id: int
    ):
        get_annotation_upload_data_url = urljoin(
            self.api_url, self.URL_PRE_ANNOTATION_UPLOAD_PATH_TOKEN
        )
        response = self._request(
            get_annotation_upload_data_url,
            "post",
            data={
                "project_id": project_id,
                "team_id": team_id,
                "ids": image_ids,
                "folder_id": folder_id,
            },
            content_type=UploadAnnotationAuthData,
        )
        return response

    def get_templates(self, team_id: int):
        get_templates_url = urljoin(self.api_url, self.URL_GET_TEMPLATES)
        response = self._request(get_templates_url, "get", params={"team_id": team_id})
        return response.json()

    def start_model_training(self, team_id: int, hyper_parameters: dict) -> dict:
        start_training_url = urljoin(self.api_url, self.URL_MODELS)

        res = self._request(
            start_training_url,
            "post",
            params={"team_id": team_id},
            data=hyper_parameters,
        )
        return res.json()

    def get_model_metrics(self, team_id: int, model_id: int) -> dict:
        get_metrics_url = urljoin(
            self.api_url, self.URL_GET_MODEL_METRICS.format(model_id)
        )
        res = self._request(get_metrics_url, "get", params={"team_id": team_id})
        return res.json()

    def get_models(
        self, name: str, team_id: int, project_id: int, model_type: str
    ) -> List:
        search_model_url = urljoin(self.api_url, self.URL_MODELS)
        res = self._request(
            search_model_url,
            "get",
            params={"team_id": team_id, "project_id": project_id, "name": name},
        )
        return res.json()

    def search_models(self, query_string: str):
        search_model_url = urljoin(self.api_url, self.URL_MODELS)
        if query_string:
            search_model_url = f"{search_model_url}?{query_string}"
        # response = self._request(search_model_url, "get",)
        return self._get_all_pages(search_model_url)

    def bulk_get_folders(self, team_id: int, project_ids: List[int]):
        get_folders_url = urljoin(self.api_url, self.URL_BULK_GET_FOLDERS)
        res = self._request(
            get_folders_url,
            "put",
            params={"team_id": team_id, "completedImagesCount": True},
            data={"project_ids": project_ids},
        )
        return res.json()

    def update_model(self, team_id: int, model_id: int, data: dict):
        update_model_url = urljoin(self.api_url, f"{self.URL_MODELS}/{model_id}")
        res = self._request(
            update_model_url, "put", data=data, params={"team_id": team_id}
        )
        return res.json()

    def delete_model(self, team_id: int, model_id: int):
        delete_model_url = urljoin(self.api_url, f"{self.URL_MODEL}/{model_id}")
        res = self._request(delete_model_url, "delete", params={"team_id": team_id})
        return res.ok

    def get_ml_model_download_tokens(self, team_id: int, model_id: int):
        get_token_url = urljoin(
            self.api_url, self.URL_GET_ML_MODEL_DOWNLOAD_TOKEN.format(model_id)
        )
        return self._request(
            get_token_url,
            "get",
            params={"team_id": team_id},
            content_type=DownloadMLModelAuthData,
        )

    def run_prediction(
        self, team_id: int, project_id: int, ml_model_id: int, image_ids: list
    ):
        prediction_url = urljoin(self.api_url, self.URL_PREDICTION)
        res = self._request(
            prediction_url,
            "post",
            data={
                "team_id": team_id,
                "project_id": project_id,
                "ml_model_id": ml_model_id,
                "image_ids": image_ids,
            },
        )
        return res

    def delete_image_annotations(
        self,
        team_id: int,
        project_id: int,
        folder_id: int = None,
        image_names: List[str] = None,
    ) -> dict:
        delete_annotations_url = urljoin(self.api_url, self.URL_DELETE_ANNOTATIONS)
        params = {"team_id": team_id, "project_id": project_id}
        data = {}
        if folder_id:
            params["folder_id"] = folder_id
        if image_names:
            data["image_names"] = image_names
        response = self._request(
            delete_annotations_url, "post", params=params, data=data
        )
        if response.ok:
            return response.json()

    def get_annotations_delete_progress(
        self, team_id: int, project_id: int, poll_id: int
    ):
        get_progress_url = urljoin(self.api_url, self.URL_DELETE_ANNOTATIONS_PROGRESS)

        response = self._request(
            get_progress_url,
            "get",
            params={"team_id": team_id, "project_id": project_id, "poll_id": poll_id},
        )
        return response.json()

    def get_limitations(
        self, team_id: int, project_id: int, folder_id: int = None
    ) -> ServiceResponse:
        get_limits_url = urljoin(self.api_url, self.URL_GET_LIMITS.format(project_id))
        return self._request(
            get_limits_url,
            "get",
            params={"team_id": team_id, "folder_id": folder_id},
            content_type=UserLimits,
        )

    def get_annotations(
        self,
        project_id: int,
        team_id: int,
        folder_id: int,
        items: List[str],
        reporter: Reporter,
    ) -> List[dict]:
        import nest_asyncio

        nest_asyncio.apply()

        query_params = {
            "team_id": team_id,
            "project_id": project_id,
        }
        if folder_id:
            query_params["folder_id"] = folder_id

        handler = StreamedAnnotations(self.default_headers, reporter)
        loop = asyncio.new_event_loop()

        return loop.run_until_complete(
            handler.get_data(
                url=urljoin(self.assets_provider_url, self.URL_GET_ANNOTATIONS),
                data=items,
                params=query_params,
                chunk_size=self.DEFAULT_CHUNK_SIZE,
                map_function=lambda x: {"image_names": x},
            )
        )

    def get_integrations(self, team_id: int) -> List[dict]:
        get_integrations_url = urljoin(
            self.api_url, self.URL_GET_INTEGRATIONS.format(team_id)
        )

        response = self._request(
            get_integrations_url, "get", params={"team_id": team_id}
        )
        if response.ok:
            return response.json().get("integrations", [])
        return []

    def attach_integrations(
        self,
        team_id: int,
        project_id: int,
        integration_id: int,
        folder_id: int,
        folder_name: str = None,
    ) -> bool:
        attach_integrations_url = urljoin(
            self.api_url, self.URL_ATTACH_INTEGRATIONS.format(team_id)
        )
        data = {
            "team_id": team_id,
            "project_id": project_id,
            "folder_id": folder_id,
            "integration_id": integration_id,
        }
        if folder_name:
            data["customer_folder_name"] = folder_name
        response = self._request(attach_integrations_url, "post", data=data)
        return response.ok

    def saqul_query(
        self, team_id: int, project_id: int, query: str, folder_id: int
    ) -> ServiceResponse:
        CHUNK_SIZE = 50
        query_url = urljoin(self.api_url, self.URL_SAQUL_QUERY)
        params = {
            "team_id": team_id,
            "project_id": project_id,
        }
        if folder_id:
            params["folder_id"] = folder_id
        data = {"query": query, "image_index": 0}
        items = []
        for _ in range(self.MAX_ITEMS_COUNT):
            response = self._request(query_url, "post", params=params, data=data)
            if response.ok:
                response_items = response.json()
                items.extend(response_items)
                if len(response_items) < CHUNK_SIZE:
                    service_response = ServiceResponse(response)
                    service_response.data = items
                    return service_response
                data["image_index"] += CHUNK_SIZE
            return ServiceResponse(response)

    def validate_saqul_query(self, team_id: int, project_id: int, query: str) -> dict:
        validate_query_url = urljoin(self.api_url, self.URL_VALIDATE_SAQUL_QUERY)
        params = {
            "team_id": team_id,
            "project_id": project_id,
        }
        data = {
            "query": query,
        }
        return self._request(
            validate_query_url, "post", params=params, data=data
        ).json()
