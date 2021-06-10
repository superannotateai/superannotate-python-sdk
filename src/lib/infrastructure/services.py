from abc import abstractmethod
from contextlib import contextmanager
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
        self._auth_token = auth_token
        self.logger = logger
        self._paginate_by = paginate_by
        self.team_id = auth_token.split("=")[-1]

    @property
    def default_headers(self):
        return {
            "Authorization": self._auth_token,
            "authtype": self.AUTH_TYPE,
            "User-Agent": constance.__version__,
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
        self, url, method="get", data=None, headers=None, params=None
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

    def _get_page(self, url, offset):
        splitter = "&" if "?" in url else "?"
        url = f"{url}{splitter}offset={offset}"

        response = self._request(url)
        if response.status_code != 200:
            raise AppException(f"Got invalid response for url {url}: {response.text}.")
        data = response.json()
        remains_count = data.get("count") - offset
        return data, remains_count

    def _get_all_pages(self, url, offset=0):
        total = list()

        while True:
            resources, remains_count = self._get_page(url, offset)
            total.extend(resources)
            if remains_count <= 0:
                break
            offset += self.paginate_by
        return total

    @abstractmethod
    def create_image(
        self,
        project_id,
        team_id,
        images,
        annotation_status_code,
        upload_state_code,
        meta,
        annotation_json_path,
        annotation_bluemap_path,
    ):
        raise NotImplementedError


class SuperannotateBackendService(BaseBackendService):
    """
    Manage projects, images and team in the Superannotate
    """

    URL_LIST_PROJECTS = "projects"
    URL_CREATE_PROJECT = "project"
    URL_GET_PROJECT = "project/{}"
    URL_GET_FOLDER_BY_NAME = "folder/getFolderByName"
    URL_CREATE_IMAGE = "/image/ext-create"

    def get_projects(self, query_string: str = None) -> list:
        url = urljoin(self.api_url, self.URL_LIST_PROJECTS)
        if query_string:
            url = f"{url}?{query_string}"
        return [
            project for page in self._get_all_pages(url) for project in page["data"]
        ]

    def create_project(self, project_data: dict) -> dict:
        create_project_url = urljoin(self.api_url, self.URL_CREATE_PROJECT)
        res = self._request(create_project_url, "post", project_data)
        return res.json()

    def delete_project(self, uuid: int) -> bool:
        delete_project_url = urljoin(self.api_url, self.URL_GET_PROJECT.format(uuid))
        res = self._request(delete_project_url, "delete")
        return res.ok

    def update_project(self, data: dict) -> bool:
        update_project_url = urljoin(
            self.api_url, self.URL_GET_PROJECT.format(data["uuid"])
        )
        res = self._request(
            update_project_url, "put", data, params={"team_id": data["team_id"]},
        )
        return res.ok

    def create_image(
        self,
        project_id,
        team_id,
        images,
        annotation_status_code,
        upload_state_code,
        meta,
        annotation_json_path,
        annotation_bluemap_path,
    ):
        data = {
            "project_id": project_id,
            "team_id": team_id,
            "images": images,
            "annotation_status": annotation_status_code,
            "upload_state_code": upload_state_code,
            "meta": meta,
            "annotation_json_path": annotation_json_path,
            "annotation_bluemap_path": annotation_bluemap_path,
        }
        create_image_url = urljoin(self.api_url, self.URL_CREATE_IMAGE)
        self._request(create_image_url, "post", data)

    def get_s3_upload_auth_token(self, team_id: int, folder_id: int, project_id: int):
        auth_token_url = urljoin(
            self.api_url,
            self.URL_GET_PROJECT.format(project_id) + "/sdkImageUploadToken",
        )
        response = self._request(
            auth_token_url, "get", params={"team_id": team_id, "folder_id": folder_id}
        )
        return response.json()

    def get_folder(self, query_string):
        get_folder_url = urljoin(
            self.api_url, self.URL_GET_FOLDER_BY_NAME, query_string
        )
        response = self._request(get_folder_url, "get")
        return response.json()
