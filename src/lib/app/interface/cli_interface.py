import io
import logging
import os
from pathlib import Path

import src.lib.core as constances
from src.lib.app.interface.base_interface import BaseInterfaceFacade
from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ


logger = logging.getLogger()


class CLIFacade(BaseInterfaceFacade):
    def create_project(
        self, project_name: str, project_description: str, project_type: str
    ) -> dict:
        project_type = constances.ProjectType[project_type.upper()].value
        response = self.controller.create_project(
            project_name, project_description, project_type
        )
        if response.errors:
            return response.errors
        return response.data

    def upload_images_from_folder_to_project(
        self,
        project: str,
        folder_path: str,
        extensions: str = constances.DEFAULT_IMAGE_EXTENSIONS,
        annotation_status: str = constances.AnnotationStatus.NOT_STARTED.value,
        exclude_file_patterns=constances.DEFAULT_FILE_EXCLUDE_PATTERNS,
        recursive_subfolders=False,
        image_quality_in_editor=None,
    ):
        paths = []
        for extension in extensions:
            if not recursive_subfolders:
                paths += list(Path(folder_path).glob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    paths += list(Path(folder_path).glob(f"*.{extension.upper()}"))
            else:
                paths += list(Path(folder_path).rglob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    paths += list(Path(folder_path).rglob(f"*.{extension.upper()}"))

        filtered_paths = []
        for path in paths:
            not_in_exclude_list = [
                x not in Path(path).name for x in exclude_file_patterns
            ]
            if all(not_in_exclude_list):
                filtered_paths.append(path)

        controller = self.controller
        project_list_condition = Condition("name", project, EQ) & Condition(
            "team_id", controller.team_id, EQ
        )
        projects = controller.projects.get_all(condition=project_list_condition)
        if projects:
            project = projects[0]
            if not folder_path:
                folder_id = project.folder_id
            else:
                folder_condition = (
                    Condition("project_id", project.uuid, EQ)
                    & Condition("team_id", controller.team_id, EQ)
                    & Condition("name", folder_path, EQ)
                )
                folder_id = controller.folders.get_one(folder_condition).uuid
            image_info_entities = []
            for image_path in filtered_paths:
                with open(image_path, "rb") as f:
                    file = io.BytesIO(f.read())

                response = self.controller.upload_image_to_s3(
                    project=project,
                    image_path=image_path,
                    image=file,
                    folder_id=folder_id,
                )
                image_info_entities.append(response.data)

            if image_info_entities:
                self.controller.upload_images(
                    project=project,
                    images=image_info_entities,
                    annotation_status=annotation_status,
                    image_quality=image_quality_in_editor,
                )
