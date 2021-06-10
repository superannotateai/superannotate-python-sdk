from typing import List

import src.lib.core as constances
from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ
from src.lib.core.entities import ProjectEntity
from src.lib.core.exceptions import AppException
from src.lib.core.response import Response
from src.lib.core.usecases import CreateProjectUseCase
from src.lib.core.usecases import DeleteProjectUseCase
from src.lib.core.usecases import GetProjectsUseCase
from src.lib.core.usecases import UpdateProjectUseCase
from src.lib.core.usecases import UploadS3ImageUseCase
from src.lib.infrastructure.repositories import ConfigRepository
from src.lib.infrastructure.repositories import FolderRepository
from src.lib.infrastructure.repositories import ProjectRepository
from src.lib.infrastructure.repositories import S3Repository
from src.lib.infrastructure.services import SuperannotateBackendService


class BaseController:
    def __init__(self, backend_client: SuperannotateBackendService, response: Response):
        self._backend_client = backend_client
        self._response = response
        self._s3_upload_auth_data = None

    @property
    def response(self):
        return self._response

    @property
    def projects(self):
        return ProjectRepository(self._backend_client)

    @property
    def configs(self):
        return ConfigRepository()

    @property
    def folders(self):
        return FolderRepository(self._backend_client)

    @property
    def team_id(self) -> int:
        return int(self.configs.get_one("token").value.split("=")[-1])

    def get_s3_repository(
        self, team_id: int, project_id: int, folder_id: int, bucket: str
    ):
        auth_data = self._backend_client.get_s3_upload_auth_token(
            team_id, folder_id, project_id
        )
        self._s3_upload_auth_data = auth_data
        return S3Repository(
            auth_data["accessKeyId"],
            auth_data["secretAccessKey"],
            auth_data["sessionToken"],
            bucket,
        )


class Controller(BaseController):
    def search_project(self, name: str) -> Response:
        use_case = GetProjectsUseCase(
            self.response, Condition("project_name", name, EQ), self.projects
        )
        use_case.execute()
        return self.response

    def create_project(
        self, name: str, description: str, project_type: str
    ) -> Response:
        project_type = constances.ProjectType[project_type.upper()].value
        entity = ProjectEntity(
            name=name, description=description, project_type=project_type
        )
        use_case = CreateProjectUseCase(self.response, entity, self.projects)
        use_case.execute()
        return self.response

    def delete_project(self, name: str):
        entities = self.projects.get_all(
            Condition("teams_id", self.team_id, EQ) & Condition("name", name, EQ)
        )
        if entities and len(entities) == 1:
            use_case = DeleteProjectUseCase(self.response, entities[0], self.projects)
            use_case.execute()
            return self.response
        raise AppException("There are duplicated names.")

    def update_project(self, name: str, project_data: dict) -> Response:
        entities = self.projects.get_all(
            Condition("teams_id", self.team_id, EQ) & Condition("name", name, EQ)
        )
        if entities and len(entities) == 1:
            entity = ProjectEntity(name=name, **project_data)
            use_case = UpdateProjectUseCase(self.response, entity, self.projects)
            use_case.execute()
            return self.response
        raise AppException("There are duplicated names.")

    def upload_s3_images(
        self,
        project_name: str,
        image_paths: List[str],  # images to upload
        s3_bucket: str,
        folder_path: str = None,  # project folder path
        annotation_status: str = None,
        image_quality: str = None,
    ):
        project_list_condition = Condition(
            "project_name", project_name, EQ
        ) & Condition("team_id", self.team_id, EQ)
        projects = self.projects.get_all(condition=project_list_condition)
        if projects:
            project = projects[0]
            if not folder_path:
                folder_id = project.folder_id
            else:
                folder_condition = (
                    Condition("project_id", project.uuid, EQ)
                    & Condition("team_id", self.team_id, EQ)
                    & Condition("name", folder_path, EQ)
                )
                folder_id = self.folders.get_one(folder_condition).uuid

            s3_repo = self.get_s3_repository(
                self.team_id,
                project.uuid,
                folder_id,
                self._s3_upload_auth_data["bucket"],
            )
            use_case = UploadS3ImageUseCase(
                response=self.response,
                project=project,
                backend_service_provider=self._backend_client,
                image_paths=image_paths,
                bucket=s3_bucket,
                s3_repo=s3_repo,
                upload_path=self._s3_upload_auth_data["filePath"],
                annotation_status=annotation_status,
                image_quality=image_quality,
            )
            use_case.execute()
            return self.response

    def clone_project(
        self,
        name: str,
        from_name: str,
        project_description: str,
        copy_annotation_classes=True,
        copy_settings=True,
        copy_workflow=True,
        copy_contributors=False,
    ):
        raise NotImplementedError

    def get_project_metadata(
        self,
        name: str,
        include_annotation_classes=False,
        include_settings=False,
        include_workflow=False,
        include_contributors=False,
        include_complete_image_count=False,
    ):
        raise NotImplementedError

    def create_project_from_metadata(self):
        # todo move to cli level
        raise NotImplementedError
