from contextlib import contextmanager
from datetime import datetime
from typing import Dict
from typing import Iterable
from typing import List
from urllib.parse import urljoin

import requests
import src.lib.core as constance
from requests.exceptions import HTTPError
from src.lib.core.exceptions import AppException
from src.lib.core.serviceproviders import SuerannotateServiceProvider


class BaseBackendService(SuerannotateServiceProvider):
    AUTH_TYPE = "sdk"
    PAGINATE_BY = 100

    """
    Base service class
    """

    def __init__(self, api_url, auth_token, logger, paginate_by=None):
        self.api_url = api_url
        self._auth_token = auth_token.value
        self.logger = logger
        self._paginate_by = paginate_by
        self.team_id = auth_token.value.split("=")[-1]

    @property
    def default_headers(self):
        return {
            "Authorization": self._auth_token,
            "authtype": self.AUTH_TYPE,
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
        self, url, method="get", data=None, headers=None, params=None,
    ) -> requests.Response:
        kwargs = {"json": data} if data else {}
        headers_dict = self.default_headers.copy()
        headers_dict.update(headers if headers else {})

        method = getattr(requests, method)
        with self.safe_api():
            response = method(url, **kwargs, headers=headers_dict, params=params)
        if response.status_code > 299:
            self.logger.error(
                f"Got {response.status_code} response for url {url}: {response.text}"
            )
        return response

    def _get_page(self, url, offset, params=None, key_field: str = None):
        splitter = "&" if "?" in url else "?"
        url = f"{url}{splitter}offset={offset}"

        response = self._request(url, params=params)
        if response.status_code != 200:
            raise AppException(f"Got invalid response for url {url}: {response.text}.")
        data = response.json()
        if data:
            if isinstance(data, dict):
                if key_field:
                    data = data[key_field]
                return data, data.get("count") - offset
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
            offset += self.paginate_by
        return total


class SuperannotateBackendService(BaseBackendService):
    """
    Manage projects, images and team in the Superannotate
    """

    URL_USERS = "users"
    URL_LIST_PROJECTS = "projects"
    URL_FOLDERS_IMAGES = "images-folders"
    URL_CREATE_PROJECT = "project"
    URL_GET_PROJECT = "project/{}"
    URL_GET_FOLDER_BY_NAME = "folder/getFolderByName"
    URL_CREATE_FOLDER = "folder"
    URL_UPDATE_FOLDER = "folder/{}"
    URL_FOLDERS = "folder"
    URL_GET_IMAGE = "image/{}"
    URL_DELETE_FOLDERS = "image/delete/images"
    URL_GET_PROJECT_SETTIGNS = "/project/{}/settings"
    URL_CREATE_IMAGE = "image/ext-create"
    URL_PROJECT_SETTIGNS = "project/{}/settings"
    URL_PROJECT_WORKFLOW = "project/{}/workflow"
    URL_SHARE_PROJECT = "project/{}/workflow"
    URL_ANNOTATION_CLASSES = "classes"
    URL_TEAM = "team"
    URL_INVITE_CONTRIBUTOR = "team/{}/invite"
    URL_PREPARE_EXPORT = "export"

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
        return self._get_all_pages(url)

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

    def update_project(self, data: dict, query_string: str = None) -> bool:
        url = urljoin(self.api_url, self.URL_GET_PROJECT.format(data["id"]))
        if query_string:
            url = f"{url}?{query_string}"
        res = self._request(url, "put", data,)
        return res.ok

    def attach_files(
        self,
        project_id: int,
        team_id: int,
        files: List[Dict],
        annotation_status_code,
        upload_state_code,
        meta,
    ):
        data = {
            "project_id": project_id,
            "team_id": team_id,
            "images": files,
            "annotation_status": annotation_status_code,
            "upload_state_code": upload_state_code,
            "meta": meta,
        }
        create_image_url = urljoin(self.api_url, self.URL_CREATE_IMAGE)
        self._request(create_image_url, "post", data)

    def get_folder(self, query_string: str):
        get_folder_url = urljoin(self.api_url, self.URL_GET_FOLDER_BY_NAME)
        if query_string:
            get_folder_url = f"{get_folder_url}?{query_string}"
        response = self._request(get_folder_url, "get")
        return response.json()

    def get_folders(self, query_string: str = None, params: dict = None):
        get_folder_url = urljoin(self.api_url, self.URL_FOLDERS_IMAGES)
        if query_string:
            get_folder_url = f"{get_folder_url}?{query_string}"
        response = self._get_all_pages(
            get_folder_url, params=params, key_field="folders"
        )
        return response

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
        return res.json()

    def get_project_settings(self, project_id: int, team_id: int):
        get_settings_url = urljoin(
            self.api_url, self.URL_PROJECT_SETTIGNS.format(project_id)
        )
        res = self._request(get_settings_url, "get", params={"team_id": team_id})
        return res.json()

    def set_project_settings(self, project_id: int, team_id: int, data: Dict):
        set_project_settings_url = urljoin(
            self.api_url, self.URL_PROJECT_SETTIGNS.format(project_id)
        )
        res = self._request(
            set_project_settings_url,
            "put",
            data={"settings": [data]},
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

    def share_project(
        self, project_id: int, team_id: int, user_id: int, user_role: int
    ):
        share_project_url = urljoin(
            self.api_url, self.URL_SHARE_PROJECT.format(project_id)
        )
        res = self._request(
            share_project_url,
            "post",
            data={"user_id": user_id, "user_role": user_role},
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
        users_url = urljoin(self.api_url, self.URL_USERS.format(project_id))

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

    def invite_contributor(self, team_id: int, email: str, user_role: str) -> bool:
        invite_contributor_url = urljoin(
            self.api_url, self.URL_INVITE_CONTRIBUTOR.format(team_id)
        )
        res = self._request(
            invite_contributor_url,
            "post",
            data={"email": email, "user_role": user_role},
        )
        return res.ok

    def delete_team_invitation(self, team_id: int, token: str, email: str) -> bool:
        invite_contributor_url = urljoin(
            self.api_url, self.URL_INVITE_CONTRIBUTOR.format(team_id)
        )
        res = self._request(
            invite_contributor_url, "delete", data={"token": token, "e_mail": email}
        )
        return res.ok

    def update_image(self, image_id: int, team_id: int, project_id: int, data: dict):
        update_image_url = urljoin(self.api_url, self.URL_GET_IMAGE.format(image_id))

        res = self._request(
            update_image_url,
            "put",
            data=data,
            params={"team_id": team_id, "project_id": project_id},
        )
        return res.ok
