import collections
import io
import json
import os
import tempfile
import warnings
from pathlib import Path
from typing import Callable
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import boto3
import lib.core as constants
from lib.app.annotation_helpers import add_annotation_bbox_to_json
from lib.app.annotation_helpers import add_annotation_comment_to_json
from lib.app.annotation_helpers import add_annotation_point_to_json
from lib.app.helpers import extract_project_folder
from lib.app.helpers import get_annotation_paths
from lib.app.helpers import get_name_url_duplicated_from_csv
from lib.app.interface.base_interface import BaseInterfaceFacade
from lib.app.interface.base_interface import TrackableMeta
from lib.app.interface.types import AnnotationStatuses
from lib.app.interface.types import AnnotationType
from lib.app.interface.types import AnnotatorRole
from lib.app.interface.types import AttachmentArg
from lib.app.interface.types import AttachmentDict
from lib.app.interface.types import ClassType
from lib.app.interface.types import EmailStr
from lib.app.interface.types import ImageQualityChoices
from lib.app.interface.types import NotEmptyStr
from lib.app.interface.types import ProjectStatusEnum
from lib.app.interface.types import ProjectTypes
from lib.app.interface.types import Setting
from lib.app.serializers import BaseSerializer
from lib.app.serializers import FolderSerializer
from lib.app.serializers import ProjectSerializer
from lib.app.serializers import SettingsSerializer
from lib.app.serializers import TeamSerializer
from lib.core import LIMITED_FUNCTIONS
from lib.core.entities import AttachmentEntity
from lib.core.entities import SettingEntity
from lib.core.entities.integrations import IntegrationEntity
from lib.core.entities.project_entities import AnnotationClassEntity
from lib.core.enums import ImageQuality
from lib.core.exceptions import AppException
from lib.core.types import AttributeGroup
from lib.core.types import MLModel
from lib.core.types import PriorityScore
from lib.core.types import Project
from lib.infrastructure.controller import Controller
from pydantic import conlist
from pydantic import parse_obj_as
from pydantic import StrictBool
from pydantic.error_wrappers import ValidationError
from superannotate.logger import get_default_logger
from tqdm import tqdm

logger = get_default_logger()


class SAClient(BaseInterfaceFacade, metaclass=TrackableMeta):
    def __init__(
        self,
        token: str = None,
        config_path: str = constants.CONFIG_PATH,
    ):
        super().__init__(token, config_path)

    def get_team_metadata(self):
        """Returns team metadata

        :return: team metadata
        :rtype: dict
        """
        response = self.controller.get_team()
        return TeamSerializer(response.data).serialize()

    def search_team_contributors(
        self,
        email: EmailStr = None,
        first_name: NotEmptyStr = None,
        last_name: NotEmptyStr = None,
        return_metadata: bool = True,
    ):
        """Search for contributors in the team

        :param email: filter by email
        :type email: str
        :param first_name: filter by first name
        :type first_name: str
        :param last_name: filter by last name
        :type last_name: str
        :param return_metadata: return metadata of contributors instead of names
        :type return_metadata: bool

        :return: metadata of found users
        :rtype: list of dicts
        """

        contributors = self.controller.search_team_contributors(
            email=email, first_name=first_name, last_name=last_name
        ).data

        if not return_metadata:
            return [contributor["email"] for contributor in contributors]
        return contributors

    def search_projects(
        self,
        name: Optional[NotEmptyStr] = None,
        return_metadata: bool = False,
        include_complete_image_count: bool = False,
        status: Optional[Union[ProjectStatusEnum, List[ProjectStatusEnum]]] = None,
    ):
        """
        Project name based case-insensitive search for projects.
        If **name** is None, all the projects will be returned.

        :param name: search string
        :type name: str

        :param return_metadata: return metadata of projects instead of names
        :type return_metadata: bool

        :param include_complete_image_count: return projects that have completed images and include the number of completed images in response.
        :type include_complete_image_count: bool

        :param status: search projects via project status
        :type status: str

        :return: project names or metadatas
        :rtype: list of strs or dicts
        """
        statuses = []
        if status:
            if isinstance(status, (list, tuple, set)):
                statuses = list(status)
            else:
                statuses = [status]
        result = self.controller.search_project(
            name=name,
            include_complete_image_count=include_complete_image_count,
            statuses=statuses,
        ).data

        if return_metadata:
            return [
                ProjectSerializer(project).serialize(
                    exclude={
                        "annotation_classes",
                        "workflows",
                        "settings",
                        "contributors",
                        "classes",
                    }
                )
                for project in result
            ]
        else:
            return [project.name for project in result]

    def create_project(
        self,
        project_name: NotEmptyStr,
        project_description: NotEmptyStr,
        project_type: NotEmptyStr,
        settings: List[Setting] = None,
    ):
        """Create a new project in the team.

        :param project_name: the new project's name
        :type project_name: str

        :param project_description: the new project's description
        :type project_description: str

        :param project_type: the new project type, Vector or Pixel.
        :type project_type: str

        :param settings: list of settings objects
        :type settings: list of dicts

        :return: dict object metadata the new project
        :rtype: dict
        """
        if settings:
            settings = parse_obj_as(List[SettingEntity], settings)
        else:
            settings = []
        response = self.controller.create_project(
            name=project_name,
            description=project_description,
            project_type=project_type,
            settings=settings,
        )
        if response.errors:
            raise AppException(response.errors)

        return ProjectSerializer(response.data).serialize()

    def create_project_from_metadata(self, project_metadata: Project):
        """Create a new project in the team using project metadata object dict.
        Mandatory keys in project_metadata are "name", "description" and "type" (Vector or Pixel)
        Non-mandatory keys: "workflow", "settings" and "annotation_classes".

        :return: dict object metadata the new project
        :rtype: dict
        """
        project_metadata = project_metadata.dict()
        response = self.controller.create_project(
            name=project_metadata["name"],
            description=project_metadata.get("description"),
            project_type=project_metadata["type"],
            settings=parse_obj_as(
                List[SettingEntity], project_metadata.get("settings", [])
            ),
            classes=project_metadata.get("classes", []),
            workflows=project_metadata.get("workflows", []),
            instructions_link=project_metadata.get("instructions_link"),
        )
        if response.errors:
            raise AppException(response.errors)
        return ProjectSerializer(response.data).serialize()

    def clone_project(
        self,
        project_name: Union[NotEmptyStr, dict],
        from_project: Union[NotEmptyStr, dict],
        project_description: Optional[NotEmptyStr] = None,
        copy_annotation_classes: Optional[StrictBool] = True,
        copy_settings: Optional[StrictBool] = True,
        copy_workflow: Optional[StrictBool] = True,
        copy_contributors: Optional[StrictBool] = False,
    ):
        """Create a new project in the team using annotation classes and settings from from_project.

        :param project_name: new project's name
        :type project_name: str
        :param from_project: the name of the project being used for duplication
        :type from_project: str
        :param project_description: the new project's description. If None, from_project's
                                    description will be used
        :type project_description: str
        :param copy_annotation_classes: enables copying annotation classes
        :type copy_annotation_classes: bool
        :param copy_settings: enables copying project settings
        :type copy_settings: bool
        :param copy_workflow: enables copying project workflow
        :type copy_workflow: bool
        :param copy_contributors: enables copying project contributors
        :type copy_contributors: bool

        :return: dict object metadata of the new project
        :rtype: dict
        """
        response = self.controller.clone_project(
            name=project_name,
            from_name=from_project,
            project_description=project_description,
            copy_annotation_classes=copy_annotation_classes,
            copy_settings=copy_settings,
            copy_workflow=copy_workflow,
            copy_contributors=copy_contributors,
        )
        if response.errors:
            raise AppException(response.errors)
        return ProjectSerializer(response.data).serialize()

    def create_folder(self, project: NotEmptyStr, folder_name: NotEmptyStr):
        """Create a new folder in the project.

        :param project: project name
        :type project: str
        :param folder_name: the new folder's name
        :type folder_name: str

        :return: dict object metadata the new folder
        :rtype: dict
        """

        res = self.controller.create_folder(project=project, folder_name=folder_name)
        if res.data:
            folder = res.data
            logger.info(f"Folder {folder.name} created in project {project}")
            return folder.to_dict()
        if res.errors:
            raise AppException(res.errors)

    def delete_project(self, project: Union[NotEmptyStr, dict]):
        """Deletes the project

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        """
        name = project
        if isinstance(project, dict):
            name = project["name"]
        self.controller.delete_project(name=name)

    def rename_project(self, project: NotEmptyStr, new_name: NotEmptyStr):
        """Renames the project

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param new_name: project's new name
        :type new_name: str
        """

        response = self.controller.update_project(
            name=project, project_data={"name": new_name}
        )
        if response.errors:
            raise AppException(response.errors)
        logger.info(
            "Successfully renamed project %s to %s.", project, response.data.name
        )
        return ProjectSerializer(response.data).serialize()

    def get_folder_metadata(self, project: NotEmptyStr, folder_name: NotEmptyStr):
        """Returns folder metadata

        :param project: project name
        :type project: str
        :param folder_name: folder's name
        :type folder_name: str

        :return: metadata of folder
        :rtype: dict
        """
        result = self.controller.get_folder(
            project_name=project, folder_name=folder_name
        ).data
        if not result:
            raise AppException("Folder not found.")
        return FolderSerializer(result).serialize()

    def delete_folders(self, project: NotEmptyStr, folder_names: List[NotEmptyStr]):
        """Delete folder in project.

        :param project: project name
        :type project: str
        :param folder_names: to be deleted folders' names
        :type folder_names: list of strs
        """

        res = self.controller.delete_folders(
            project_name=project, folder_names=folder_names
        )
        if res.errors:
            raise AppException(res.errors)
        logger.info(f"Folders {folder_names} deleted in project {project}")

    def search_folders(
        self,
        project: NotEmptyStr,
        folder_name: Optional[NotEmptyStr] = None,
        return_metadata: Optional[StrictBool] = False,
    ):
        """Folder name based case-insensitive search for folders in project.

        :param project: project name
        :type project: str
        :param folder_name: the new folder's name
        :type folder_name: str. If  None, all the folders in the project will be returned.
        :param return_metadata: return metadata of folders instead of names
        :type return_metadata: bool

        :return: folder names or metadatas
        :rtype: list of strs or dicts
        """

        response = self.controller.search_folders(
            project_name=project, folder_name=folder_name, include_users=return_metadata
        )
        if response.errors:
            raise AppException(response.errors)
        data = response.data
        if return_metadata:
            return [FolderSerializer(folder).serialize() for folder in data]
        return [folder.name for folder in data]

    def copy_image(
        self,
        source_project: Union[NotEmptyStr, dict],
        image_name: NotEmptyStr,
        destination_project: Union[NotEmptyStr, dict],
        include_annotations: Optional[StrictBool] = False,
        copy_annotation_status: Optional[StrictBool] = False,
        copy_pin: Optional[StrictBool] = False,
    ):
        """Copy image to a project. The image's project is the same as destination
        project then the name will be changed to <image_name>_(<num>).<image_ext>,
        where <num> is the next available number deducted from project image list.

        :param source_project: project name plus optional subfolder in the project (e.g., "project1/folder1") or
                               metadata of the project of source project
        :type source_project: str or dict
        :param image_name: image name
        :type image_name: str
        :param destination_project: project name or metadata of the project of destination project
        :type destination_project: str or dict
        :param include_annotations: enables annotations copy
        :type include_annotations: bool
        :param copy_annotation_status: enables annotations status copy
        :type copy_annotation_status: bool
        :param copy_pin: enables image pin status copy
        :type copy_pin: bool
        """
        source_project_name, source_folder_name = extract_project_folder(source_project)

        destination_project, destination_folder = extract_project_folder(
            destination_project
        )
        source_project_metadata = self.controller.get_project_metadata(
            source_project_name
        ).data
        destination_project_metadata = self.controller.get_project_metadata(
            destination_project
        ).data

        if destination_project_metadata["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ] or source_project_metadata["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(
                LIMITED_FUNCTIONS[source_project_metadata["project"].type]
            )

        response = self.controller.copy_image(
            from_project_name=source_project_name,
            from_folder_name=source_folder_name,
            to_project_name=destination_project,
            to_folder_name=destination_folder,
            image_name=image_name,
            copy_annotation_status=copy_annotation_status,
        )
        if response.errors:
            raise AppException(response.errors)

        if include_annotations:
            self.controller.copy_image_annotation_classes(
                from_project_name=source_project_name,
                from_folder_name=source_folder_name,
                to_folder_name=destination_folder,
                to_project_name=destination_project,
                image_name=image_name,
            )
        if copy_pin:
            self.controller.update_image(
                project_name=destination_project,
                folder_name=destination_folder,
                image_name=image_name,
                is_pinned=1,
            )
        logger.info(
            f"Copied image {source_project}/{image_name}"
            f" to {destination_project}/{destination_folder}."
        )

    def get_project_metadata(
        self,
        project: Union[NotEmptyStr, dict],
        include_annotation_classes: Optional[StrictBool] = False,
        include_settings: Optional[StrictBool] = False,
        include_workflow: Optional[StrictBool] = False,
        include_contributors: Optional[StrictBool] = False,
        include_complete_image_count: Optional[StrictBool] = False,
    ):
        """Returns project metadata

        :param project: project name
        :type project: str
        :param include_annotation_classes: enables project annotation classes output under
                                           the key "annotation_classes"
        :type include_annotation_classes: bool
        :param include_settings: enables project settings output under
                                 the key "settings"
        :type include_settings: bool
        :param include_workflow: enables project workflow output under
                                 the key "workflow"
        :type include_workflow: bool
        :param include_contributors: enables project contributors output under
                                 the key "contributors"
        :type include_contributors: bool

        :param include_complete_image_count: enables project complete image count output under
                                 the key "completed_images_count"
        :type include_complete_image_count: bool

        :return: metadata of project
        :rtype: dict
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.get_project_metadata(
            project_name,
            include_annotation_classes,
            include_settings,
            include_workflow,
            include_contributors,
            include_complete_image_count,
        ).data

        metadata = ProjectSerializer(response["project"]).serialize()

        for elem in "classes", "workflows", "contributors":
            if response.get(elem):
                metadata[elem] = [
                    BaseSerializer(attribute).serialize()
                    for attribute in response[elem]
                ]
        return metadata

    def get_project_settings(self, project: Union[NotEmptyStr, dict]):
        """Gets project's settings.

        Return value example: [{ "attribute" : "Brightness", "value" : 10, ...},...]

        :param project: project name or metadata
        :type project: str or dict

        :return: project settings
        :rtype: list of dicts
        """
        project_name, folder_name = extract_project_folder(project)
        settings = self.controller.get_project_settings(project_name=project_name)
        settings = [
            SettingsSerializer(attribute).serialize() for attribute in settings.data
        ]
        return settings

    def get_project_workflow(self, project: Union[str, dict]):
        """Gets project's workflow.

        Return value example: [{ "step" : <step_num>, "className" : <annotation_class>, "tool" : <tool_num>, ...},...]

        :param project: project name or metadata
        :type project: str or dict

        :return: project workflow
        :rtype: list of dicts
        """
        project_name, folder_name = extract_project_folder(project)
        workflow = self.controller.get_project_workflow(project_name=project_name)
        if workflow.errors:
            raise AppException(workflow.errors)
        return workflow.data

    def search_annotation_classes(
        self, project: Union[NotEmptyStr, dict], name_contains: Optional[str] = None
    ):
        """Searches annotation classes by name_prefix (case-insensitive)

        :param project: project name
        :type project: str
        :param name_contains:  search string. Returns those classes,
         where the given string is found anywhere within its name. If None, all annotation classes will be returned.
        :type name_prefix: str

        :return: annotation classes of the project
        :rtype: list of dicts
        """
        project_name, folder_name = extract_project_folder(project)
        classes = self.controller.search_annotation_classes(project_name, name_contains)
        classes = [BaseSerializer(attribute).serialize() for attribute in classes.data]
        return classes

    def set_project_default_image_quality_in_editor(
        self,
        project: Union[NotEmptyStr, dict],
        image_quality_in_editor: Optional[str],
    ):
        """Sets project's default image quality in editor setting.

        :param project: project name or metadata
        :type project: str or dict
        :param image_quality_in_editor: new setting value, should be "original" or "compressed"
        :type image_quality_in_editor: str
        """
        project_name, folder_name = extract_project_folder(project)
        image_quality_in_editor = ImageQuality.get_value(image_quality_in_editor)

        response = self.controller.set_project_settings(
            project_name=project_name,
            new_settings=[
                {"attribute": "ImageQuality", "value": image_quality_in_editor}
            ],
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def pin_image(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: str,
        pin: Optional[StrictBool] = True,
    ):
        """Pins (or unpins) image

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param pin: sets to pin if True, else unpins image
        :type pin: bool
        """
        project_name, folder_name = extract_project_folder(project)
        self.controller.update_image(
            project_name=project_name,
            image_name=image_name,
            folder_name=folder_name,
            is_pinned=int(pin),
        )

    def set_images_annotation_statuses(
        self,
        project: Union[NotEmptyStr, dict],
        annotation_status: NotEmptyStr,
        image_names: Optional[List[NotEmptyStr]] = None,
    ):
        """Sets annotation statuses of images

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_names: image names. If None, all the images in the project will be used
        :type image_names: list of str
        :param annotation_status: annotation status to set,
               should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_status: str
        """
        warning_msg = (
            "We're deprecating the set_images_annotation_statuses function. Please use set_annotation_statuses instead. "
            "Learn more. \n"
            "https://superannotate.readthedocs.io/en/stable/superannotate.sdk.html#superannotate.set_annotation_statuses"
        )
        logger.warning(warning_msg)
        warnings.warn(warning_msg, DeprecationWarning)
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.set_images_annotation_statuses(
            project_name, folder_name, image_names, annotation_status
        )
        if response.errors:
            raise AppException(response.errors)
        logger.info("Annotations status of images changed")

    def delete_images(
        self, project: Union[NotEmptyStr, dict], image_names: Optional[List[str]] = None
    ):
        """Delete images in project.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_names: to be deleted images' names. If None, all the images will be deleted
        :type image_names: list of strs
        """
        project_name, folder_name = extract_project_folder(project)

        if not isinstance(image_names, list) and image_names is not None:
            raise AppException("Image_names should be a list of str or None.")

        response = self.controller.delete_images(
            project_name=project_name, folder_name=folder_name, image_names=image_names
        )
        if response.errors:
            raise AppException(response.errors)

        logger.info(
            f"Images deleted in project {project_name}{'/' + folder_name if folder_name else ''}"
        )

    def assign_items(
        self, project: Union[NotEmptyStr, dict], items: List[str], user: str
    ):
        """Assigns items  to a user. The assignment role, QA or Annotator, will
        be deduced from the user's role in the project. The type of the objects` image, video or text
        will be deduced from the project type. With SDK, the user can be
        assigned to a role in the project with the share_project function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param items: list of items to assign
        :type item_names: list of str
        :param user: user email
        :type user: str
        """

        project_name, folder_name = extract_project_folder(project)

        response = self.controller.assign_items(project_name, folder_name, items, user)

        if not response.errors:
            logger.info(f"Assign items to user {user}")
        else:
            raise AppException(response.errors)

    def unassign_items(
        self, project: Union[NotEmptyStr, dict], items: List[NotEmptyStr]
    ):
        """Removes assignment of given items for all assignees. With SDK,
        the user can be assigned to a role in the project with the share_project
        function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param items: list of items to unassign
        :type item_names: list of str
        """
        project_name, folder_name = extract_project_folder(project)

        response = self.controller.un_assign_items(
            project_name=project_name, folder_name=folder_name, item_names=items
        )
        if response.errors:
            raise AppException(response.errors)

    def assign_images(
        self, project: Union[NotEmptyStr, dict], image_names: List[str], user: str
    ):
        """Assigns images to a user. The assignment role, QA or Annotator, will
        be deduced from the user's role in the project. With SDK, the user can be
        assigned to a role in the project with the share_project function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_names: list of image names to assign
        :type image_names: list of str
        :param user: user email
        :type user: str
        """

        warning_msg = (
            "We're deprecating the assign_images function. Please use assign_items instead."
            "Learn more. \n"
            "https://superannotate.readthedocs.io/en/stable/superannotate.sdk.html#superannotate.assign_items"
        )
        logger.warning(warning_msg)
        warnings.warn(warning_msg, DeprecationWarning)
        project_name, folder_name = extract_project_folder(project)
        project = self.controller.get_project_metadata(project_name).data

        if project["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(LIMITED_FUNCTIONS[project["project"].type])

        contributors = (
            self.controller.get_project_metadata(
                project_name=project_name, include_contributors=True
            )
            .data["project"]
            .users
        )
        contributor = None
        for c in contributors:
            if c["user_id"] == user:
                contributor = user

        if not contributor:
            logger.warning(
                f"Skipping {user}. {user} is not a verified contributor for the {project_name}"
            )
            return

        response = self.controller.assign_images(
            project_name, folder_name, image_names, user
        )
        if not response.errors:
            logger.info(f"Assign images to user {user}")
        else:
            raise AppException(response.errors)

    def unassign_images(
        self, project: Union[NotEmptyStr, dict], image_names: List[NotEmptyStr]
    ):
        """Removes assignment of given images for all assignees. With SDK,
        the user can be assigned to a role in the project with the share_project
        function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_names: list of images to unassign
        :type image_names: list of str
        """

        warning_msg = (
            "We're deprecating the unassign_images function. Please use unassign_items instead."
            "Learn more. \n"
            "https://superannotate.readthedocs.io/en/stable/superannotate.sdk.html#superannotate.unassign_items"
        )
        logger.warning(warning_msg)
        warnings.warn(warning_msg, DeprecationWarning)
        project_name, folder_name = extract_project_folder(project)

        response = self.controller.un_assign_items(
            project_name=project_name, folder_name=folder_name, image_names=image_names
        )
        if response.errors:
            raise AppException(response.errors)

    def unassign_folder(self, project_name: NotEmptyStr, folder_name: NotEmptyStr):
        """Removes assignment of given folder for all assignees.
        With SDK, the user can be assigned to a role in the project
        with the share_project function.

        :param project_name: project name
        :type project_name: str
        :param folder_name: folder name to remove assignees
        :type folder_name: str
        """
        response = self.controller.un_assign_folder(
            project_name=project_name, folder_name=folder_name
        )
        if response.errors:
            raise AppException(response.errors)

    def assign_folder(
        self,
        project_name: NotEmptyStr,
        folder_name: NotEmptyStr,
        users: List[NotEmptyStr],
    ):
        """Assigns folder to users. With SDK, the user can be
        assigned to a role in the project with the share_project function.

        :param project_name: project name or metadata of the project
        :type project_name: str or dict
        :param folder_name: folder name to assign
        :type folder_name: str
        :param users: list of user emails
        :type users: list of str
        """

        contributors = (
            self.controller.get_project_metadata(
                project_name=project_name, include_contributors=True
            )
            .data["project"]
            .users
        )
        verified_users = [i["user_id"] for i in contributors]
        verified_users = set(users).intersection(set(verified_users))
        unverified_contributor = set(users) - verified_users

        for user in unverified_contributor:
            logger.warning(
                f"Skipping {user} from assignees. {user} is not a verified contributor for the {project_name}"
            )

        if not verified_users:
            return

        response = self.controller.assign_folder(
            project_name=project_name,
            folder_name=folder_name,
            users=list(verified_users),
        )

        if response.errors:
            raise AppException(response.errors)

    def upload_images_from_folder_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        folder_path: Union[NotEmptyStr, Path],
        extensions: Optional[
            Union[List[NotEmptyStr], Tuple[NotEmptyStr]]
        ] = constants.DEFAULT_IMAGE_EXTENSIONS,
        annotation_status="NotStarted",
        from_s3_bucket=None,
        exclude_file_patterns: Optional[
            Iterable[NotEmptyStr]
        ] = constants.DEFAULT_FILE_EXCLUDE_PATTERNS,
        recursive_subfolders: Optional[StrictBool] = False,
        image_quality_in_editor: Optional[str] = None,
    ):
        """Uploads all images with given extensions from folder_path to the project.
        Sets status of all the uploaded images to set_status if it is not None.

        If an image with existing name already exists in the project it won't be uploaded,
        and its path will be appended to the third member of return value of this
        function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str or dict

        :param folder_path: from which folder to upload the images
        :type folder_path: Path-like (str or Path)

        :param extensions: tuple or list of filename extensions to include from folder
        :type extensions: tuple or list of strs

        :param annotation_status: value to set the annotation statuses of the uploaded images
         NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_status: str

        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str

        :param exclude_file_patterns: filename patterns to exclude from uploading,
                                     default value is to exclude SuperAnnotate export related ["___save.png", "___fuse.png"]
        :type exclude_file_patterns: list or tuple of strs

        :param recursive_subfolders: enable recursive subfolder parsing
        :type recursive_subfolders: bool

        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
               Can be either "compressed" or "original".  If None then the default value in project settings will be used.
        :type image_quality_in_editor: str

        :return: uploaded, could-not-upload, existing-images filepaths
        :rtype: tuple (3 members) of list of strs
        """

        project_name, folder_name = extract_project_folder(project)
        if recursive_subfolders:
            logger.info(
                "When using recursive subfolder parsing same name images in different subfolders will overwrite each other."
            )
        if not isinstance(extensions, (list, tuple)):
            print(extensions)
            raise AppException(
                "extensions should be a list or a tuple in upload_images_from_folder_to_project"
            )
        elif len(extensions) < 1:
            return [], [], []

        if exclude_file_patterns:
            exclude_file_patterns = list(exclude_file_patterns) + list(
                constants.DEFAULT_FILE_EXCLUDE_PATTERNS
            )
            exclude_file_patterns = list(set(exclude_file_patterns))

        project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")

        logger.info(
            "Uploading all images with extensions %s from %s to project %s. Excluded file patterns are: %s.",
            extensions,
            folder_path,
            project_folder_name,
            exclude_file_patterns,
        )

        use_case = self.controller.upload_images_from_folder_to_project(
            project_name=project_name,
            folder_name=folder_name,
            folder_path=folder_path,
            extensions=extensions,
            annotation_status=annotation_status,
            from_s3_bucket=from_s3_bucket,
            exclude_file_patterns=exclude_file_patterns,
            recursive_sub_folders=recursive_subfolders,
            image_quality_in_editor=image_quality_in_editor,
        )
        images_to_upload, duplicates = use_case.images_to_upload
        if len(duplicates):
            logger.warning(
                "%s already existing images found that won't be uploaded.",
                len(duplicates),
            )
        logger.info(
            "Uploading %s images to project %s.",
            len(images_to_upload),
            project_folder_name,
        )
        if not images_to_upload:
            return [], [], duplicates
        if use_case.is_valid():
            with tqdm(
                total=len(images_to_upload), desc="Uploading images"
            ) as progress_bar:
                for _ in use_case.execute():
                    progress_bar.update(1)
            return use_case.data
        raise AppException(use_case.response.errors)

    def get_project_image_count(
        self,
        project: Union[NotEmptyStr, dict],
        with_all_subfolders: Optional[StrictBool] = False,
    ):
        """Returns number of images in the project.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param with_all_subfolders: enables recursive folder counting
        :type with_all_subfolders: bool

        :return: number of images in the project
        :rtype: int
        """

        project_name, folder_name = extract_project_folder(project)

        response = self.controller.get_project_image_count(
            project_name=project_name,
            folder_name=folder_name,
            with_all_subfolders=with_all_subfolders,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def download_image_annotations(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: NotEmptyStr,
        local_dir_path: Union[str, Path],
    ):
        """Downloads annotations of the image (JSON and mask if pixel type project)
        to local_dir_path.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param local_dir_path: local directory path to download to
        :type local_dir_path: Path-like (str or Path)

        :return: paths of downloaded annotations
        :rtype: tuple
        """
        project_name, folder_name = extract_project_folder(project)
        res = self.controller.download_image_annotations(
            project_name=project_name,
            folder_name=folder_name,
            image_name=image_name,
            destination=local_dir_path,
        )
        if res.errors:
            raise AppException(res.errors)
        return res.data

    def get_exports(
        self, project: NotEmptyStr, return_metadata: Optional[StrictBool] = False
    ):
        """Get all prepared exports of the project.

        :param project: project name
        :type project: str
        :param return_metadata: return metadata of images instead of names
        :type return_metadata: bool

        :return: names or metadata objects of the all prepared exports of the project
        :rtype: list of strs or dicts
        """
        response = self.controller.get_exports(
            project_name=project, return_metadata=return_metadata
        )
        return response.data

    def prepare_export(
        self,
        project: Union[NotEmptyStr, dict],
        folder_names: Optional[List[NotEmptyStr]] = None,
        annotation_statuses: Optional[List[AnnotationStatuses]] = None,
        include_fuse: Optional[StrictBool] = False,
        only_pinned=False,
    ):
        """Prepare annotations and classes.json for export. Original and fused images for images with
        annotations can be included with include_fuse flag.

        :param project: project name
        :type project: str
        :param folder_names: names of folders to include in the export. If None, whole project will be exported
        :type folder_names: list of str
        :param annotation_statuses: images with which status to include, if None,
               ["NotStarted", "InProgress", "QualityCheck", "Returned", "Completed", "Skipped"]  will be chose
               list elements should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_statuses: list of strs
        :param include_fuse: enables fuse images in the export
        :type include_fuse: bool
        :param only_pinned: enable only pinned output in export. This option disables all other types of output.
        :type only_pinned: bool

        :return: metadata object of the prepared export
        :rtype: dict
        """
        project_name, folder_name = extract_project_folder(project)
        if folder_names is None:
            folders = [folder_name] if folder_name else []
        else:
            folders = folder_names
        if not annotation_statuses:
            annotation_statuses = [
                constants.AnnotationStatus.NOT_STARTED.name,
                constants.AnnotationStatus.IN_PROGRESS.name,
                constants.AnnotationStatus.QUALITY_CHECK.name,
                constants.AnnotationStatus.RETURNED.name,
                constants.AnnotationStatus.COMPLETED.name,
                constants.AnnotationStatus.SKIPPED.name,
            ]
        response = self.controller.prepare_export(
            project_name=project_name,
            folder_names=folders,
            include_fuse=include_fuse,
            only_pinned=only_pinned,
            annotation_statuses=annotation_statuses,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_videos_from_folder_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        folder_path: Union[NotEmptyStr, Path],
        extensions: Optional[
            Union[Tuple[NotEmptyStr], List[NotEmptyStr]]
        ] = constants.DEFAULT_VIDEO_EXTENSIONS,
        exclude_file_patterns: Optional[List[NotEmptyStr]] = (),
        recursive_subfolders: Optional[StrictBool] = False,
        target_fps: Optional[int] = None,
        start_time: Optional[float] = 0.0,
        end_time: Optional[float] = None,
        annotation_status: Optional[AnnotationStatuses] = "NotStarted",
        image_quality_in_editor: Optional[ImageQualityChoices] = None,
    ):
        """Uploads image frames from all videos with given extensions from folder_path to the project.
        Sets status of all the uploaded images to set_status if it is not None.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param folder_path: from which folder to upload the videos
        :type folder_path: Path-like (str or Path)
        :param extensions: tuple or list of filename extensions to include from folder
        :type extensions: tuple or list of strs
        :param exclude_file_patterns: filename patterns to exclude from uploading
        :type exclude_file_patterns: listlike of strs
        :param recursive_subfolders: enable recursive subfolder parsing
        :type recursive_subfolders: bool
        :param target_fps: how many frames per second need to extract from the video (approximate).
                           If None, all frames will be uploaded
        :type target_fps: float
        :param start_time: Time (in seconds) from which to start extracting frames
        :type start_time: float
        :param end_time: Time (in seconds) up to which to extract frames. If None up to end
        :type end_time: float
        :param annotation_status: value to set the annotation statuses of the uploaded images
            NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_status: str
        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
               Can be either "compressed" or "original".  If None then the default value in project settings will be used.
        :type image_quality_in_editor: str

        :return: uploaded and not-uploaded video frame images' filenames
        :rtype: tuple of list of strs
        """

        project_name, folder_name = extract_project_folder(project)

        video_paths = []
        for extension in extensions:
            if not recursive_subfolders:
                video_paths += list(Path(folder_path).glob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    video_paths += list(
                        Path(folder_path).glob(f"*.{extension.upper()}")
                    )
            else:
                logger.warning(
                    "When using recursive subfolder parsing same name videos "
                    "in different subfolders will overwrite each other."
                )
                video_paths += list(Path(folder_path).rglob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    video_paths += list(
                        Path(folder_path).rglob(f"*.{extension.upper()}")
                    )

        video_paths = [str(path) for path in video_paths]
        response = self.controller.upload_videos(
            project_name=project_name,
            folder_name=folder_name,
            paths=video_paths,
            target_fps=target_fps,
            start_time=start_time,
            exclude_file_patterns=exclude_file_patterns,
            end_time=end_time,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_video_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        video_path: Union[NotEmptyStr, Path],
        target_fps: Optional[int] = None,
        start_time: Optional[float] = 0.0,
        end_time: Optional[float] = None,
        annotation_status: Optional[AnnotationStatuses] = "NotStarted",
        image_quality_in_editor: Optional[ImageQualityChoices] = None,
    ):
        """Uploads image frames from video to platform. Uploaded images will have
        names "<video_name>_<frame_no>.jpg".

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param video_path: video to upload
        :type video_path: Path-like (str or Path)
        :param target_fps: how many frames per second need to extract from the video (approximate).
                           If None, all frames will be uploaded
        :type target_fps: float
        :param start_time: Time (in seconds) from which to start extracting frames
        :type start_time: float
        :param end_time: Time (in seconds) up to which to extract frames. If None up to end
        :type end_time: float
        :param annotation_status: value to set the annotation statuses of the uploaded
                                  video frames NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_status: str
        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
               Can be either "compressed" or "original".  If None then the default value in project settings will be used.
        :type image_quality_in_editor: str

        :return: filenames of uploaded images
        :rtype: list of strs
        """

        project_name, folder_name = extract_project_folder(project)

        response = self.controller.upload_videos(
            project_name=project_name,
            folder_name=folder_name,
            paths=[video_path],
            target_fps=target_fps,
            start_time=start_time,
            end_time=end_time,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def create_annotation_class(
        self,
        project: Union[Project, NotEmptyStr],
        name: NotEmptyStr,
        color: NotEmptyStr,
        attribute_groups: Optional[List[AttributeGroup]] = None,
        class_type: ClassType = "object",
    ):
        """Create annotation class in project

        :param project: project name
        :type project: str
        :param name: name for the class
        :type name: str
        :param color: RGB hex color value, e.g., "#FFFFAA"
        :type color: str
        :param attribute_groups: example:
         [ { "name": "tall", "is_multiselect": 0, "attributes": [ { "name": "yes" }, { "name": "no" } ] },
         { "name": "age", "is_multiselect": 0, "attributes": [ { "name": "young" }, { "name": "old" } ] } ]
        :type attribute_groups: list of dicts
        :param class_type: class type
        :type class_type: str

        :return: new class metadata
        :rtype: dict
        """
        if isinstance(project, Project):
            project = project.dict()
        attribute_groups = (
            list(map(lambda x: x.dict(), attribute_groups)) if attribute_groups else []
        )
        response = self.controller.create_annotation_class(
            project_name=project,
            name=name,
            color=color,
            attribute_groups=attribute_groups,
            class_type=class_type,
        )
        if response.errors:
            raise AppException(response.errors)
        return BaseSerializer(response.data).serialize()

    def delete_annotation_class(
        self, project: NotEmptyStr, annotation_class: Union[dict, NotEmptyStr]
    ):
        """Deletes annotation class from project

        :param project: project name
        :type project: str
        :param annotation_class: annotation class name or  metadata
        :type annotation_class: str or dict
        """
        self.controller.delete_annotation_class(
            project_name=project, annotation_class_name=annotation_class
        )

    def download_annotation_classes_json(
        self, project: NotEmptyStr, folder: Union[str, Path]
    ):
        """Downloads project classes.json to folder

        :param project: project name
        :type project: str
        :param folder: folder to download to
        :type folder: Path-like (str or Path)

        :return: path of the download file
        :rtype: str
        """
        response = self.controller.download_annotation_classes(
            project_name=project, download_path=folder
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def create_annotation_classes_from_classes_json(
        self,
        project: Union[NotEmptyStr, dict],
        classes_json: Union[List[AnnotationClassEntity], str, Path],
        from_s3_bucket=False,
    ):
        """Creates annotation classes in project from a SuperAnnotate format
        annotation classes.json.

        :param project: project name
        :type project: str
        :param classes_json: JSON itself or path to the JSON file
        :type classes_json: list or Path-like (str or Path)
        :param from_s3_bucket: AWS S3 bucket to use. If None then classes_json is in local filesystem
        :type from_s3_bucket: str

        :return: list of created annotation class metadatas
        :rtype: list of dicts
        """
        if isinstance(classes_json, str) or isinstance(classes_json, Path):
            if from_s3_bucket:
                from_session = boto3.Session()
                from_s3 = from_session.resource("s3")
                file = io.BytesIO()
                from_s3_object = from_s3.Object(from_s3_bucket, classes_json)
                from_s3_object.download_fileobj(file)
                file.seek(0)
                data = file
            else:
                data = open(classes_json)
            classes_json = json.load(data)
        try:
            annotation_classes = parse_obj_as(List[AnnotationClassEntity], classes_json)
        except ValidationError:
            raise AppException("Couldn't validate annotation classes.")
        logger.info(f"Creating annotation classes in project {project}.")
        response = self.controller.create_annotation_classes(
            project_name=project,
            annotation_classes=annotation_classes,
        )
        if response.errors:
            raise AppException(response.errors)
        return [BaseSerializer(i).serialize() for i in response.data]

    def download_export(
        self,
        project: Union[NotEmptyStr, dict],
        export: Union[NotEmptyStr, dict],
        folder_path: Union[str, Path],
        extract_zip_contents: Optional[StrictBool] = True,
        to_s3_bucket=None,
    ):
        """Download prepared export.

        WARNING: Starting from version 1.9.0 :ref:`download_export <ref_download_export>` additionally
        requires :py:obj:`project` as first argument.

        :param project: project name
        :type project: str
        :param export: export name
        :type export: str, dict
        :param folder_path: where to download the export
        :type folder_path: Path-like (str or Path)
        :param extract_zip_contents: if False then a zip file will be downloaded,
         if True the zip file will be extracted at folder_path
        :type extract_zip_contents: bool
        :param to_s3_bucket: AWS S3 bucket to use for download. If None then folder_path is in local filesystem.
        :type to_s3_bucket: Bucket object
        """
        project_name, folder_name = extract_project_folder(project)
        export_name = export["name"] if isinstance(export, dict) else export

        response = self.controller.download_export(
            project_name=project_name,
            export_name=export_name,
            folder_path=folder_path,
            extract_zip_contents=extract_zip_contents,
            to_s3_bucket=to_s3_bucket,
        )
        if response.errors:
            raise AppException(response.errors)
        logger.info(response.data)

    def set_image_annotation_status(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: NotEmptyStr,
        annotation_status: NotEmptyStr,
    ):
        """Sets the image annotation status

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param annotation_status: annotation status to set,
               should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_status: str

        :return: metadata of the updated image
        :rtype: dict
        """
        warning_msg = (
            "We're deprecating the set_image_annotation_status function. Please use set_annotation_statuses instead. "
            "Learn more. \n"
            "https://superannotate.readthedocs.io/en/stable/superannotate.sdk.html#superannotate.set_annotation_statuses"
        )
        logger.warning(warning_msg)
        warnings.warn(warning_msg, DeprecationWarning)
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.set_images_annotation_statuses(
            project_name, folder_name, [image_name], annotation_status
        )
        if response.errors:
            raise AppException(response.errors)
        image = self.controller.get_item(project_name, folder_name, image_name).data
        return BaseSerializer(image).serialize()

    def set_project_workflow(
        self, project: Union[NotEmptyStr, dict], new_workflow: List[dict]
    ):
        """Sets project's workflow.

        new_workflow example: [{ "step" : <step_num>, "className" : <annotation_class>, "tool" : <tool_num>,
                              "attribute":[{"attribute" : {"name" : <attribute_value>, "attribute_group" : {"name": <attribute_group>}}},
                              ...]
                              },...]

        :param project: project name or metadata
        :type project: str or dict
        :param new_workflow: new workflow list of dicts
        :type new_workflow: list of dicts
        """
        project_name, _ = extract_project_folder(project)
        response = self.controller.set_project_workflow(
            project_name=project_name, steps=new_workflow
        )
        if response.errors:
            raise AppException(response.errors)

    def download_image(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: NotEmptyStr,
        local_dir_path: Optional[Union[str, Path]] = "./",
        include_annotations: Optional[StrictBool] = False,
        include_fuse: Optional[StrictBool] = False,
        include_overlay: Optional[StrictBool] = False,
        variant: Optional[str] = "original",
    ):
        """Downloads the image (and annotation if not None) to local_dir_path

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param local_dir_path: where to download the image
        :type local_dir_path: Path-like (str or Path)
        :param include_annotations: enables annotation download with the image
        :type include_annotations: bool
        :param include_fuse: enables fuse image download with the image
        :type include_fuse: bool
        :param include_overlay: enables overlay image download with the image
        :type include_overlay: bool
        :param variant: which resolution to download, can be 'original' or 'lores'
         (low resolution used in web editor)
        :type variant: str

        :return: paths of downloaded image and annotations if included
        :rtype: tuple
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.download_image(
            project_name=project_name,
            folder_name=folder_name,
            image_name=image_name,
            download_path=str(local_dir_path),
            image_variant=variant,
            include_annotations=include_annotations,
            include_fuse=include_fuse,
            include_overlay=include_overlay,
        )
        if response.errors:
            raise AppException(response.errors)
        logger.info(f"Downloaded image {image_name} to {local_dir_path} ")
        return response.data

    def upload_annotations_from_folder_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        folder_path: Union[str, Path],
        from_s3_bucket=None,
        recursive_subfolders: Optional[StrictBool] = False,
    ):
        """Finds and uploads all JSON files in the folder_path as annotations to the project.

        The JSON files should follow specific naming convention. For Vector
        projects they should be named "<image_filename>___objects.json" (e.g., if
        image is cats.jpg the annotation filename should be cats.jpg___objects.json), for Pixel projects
        JSON file should be named "<image_filename>___pixel.json" and also second mask
        image file should be present with the name "<image_name>___save.png". In both cases
        image with <image_name> should be already present on the platform.

        Existing annotations will be overwritten.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str or dict
        :param folder_path: from which folder to upload annotations
        :type folder_path: str or dict
        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str
        :param recursive_subfolders: enable recursive subfolder parsing
        :type recursive_subfolders: bool

        :return: paths to annotations uploaded, could-not-upload, missing-images
        :rtype: tuple of list of strs
        """

        project_name, folder_name = extract_project_folder(project)
        project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")

        if recursive_subfolders:
            logger.info(
                "When using recursive subfolder parsing same name annotations in different "
                "subfolders will overwrite each other.",
            )
        logger.info(
            "The JSON files should follow a specific naming convention, matching file names already present "
            "on the platform. Existing annotations will be overwritten"
        )

        annotation_paths = get_annotation_paths(
            folder_path, from_s3_bucket, recursive_subfolders
        )

        logger.info(
            f"Uploading {len(annotation_paths)} annotations from {folder_path} to the project {project_folder_name}."
        )
        response = self.controller.upload_annotations_from_folder(
            project_name=project_name,
            folder_name=folder_name,
            annotation_paths=annotation_paths,  # noqa: E203
            client_s3_bucket=from_s3_bucket,
            folder_path=folder_path,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_preannotations_from_folder_to_project(
        self,
        project: Union[NotEmptyStr, dict],
        folder_path: Union[str, Path],
        from_s3_bucket=None,
        recursive_subfolders: Optional[StrictBool] = False,
    ):
        """Finds and uploads all JSON files in the folder_path as pre-annotations to the project.

        The JSON files should follow specific naming convention. For Vector
        projects they should be named "<image_filename>___objects.json" (e.g., if
        image is cats.jpg the annotation filename should be cats.jpg___objects.json), for Pixel projects
        JSON file should be named "<image_filename>___pixel.json" and also second mask
        image file should be present with the name "<image_name>___save.png". In both cases
        image with <image_name> should be already present on the platform.

        Existing pre-annotations will be overwritten.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param folder_path: from which folder to upload the pre-annotations
        :type folder_path: Path-like (str or Path)
        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str
        :param recursive_subfolders: enable recursive subfolder parsing
        :type recursive_subfolders: bool

        :return: paths to pre-annotations uploaded and could-not-upload
        :rtype: tuple of list of strs
        """
        project_name, folder_name = extract_project_folder(project)
        project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")
        project = self.controller.get_project_metadata(project_name).data
        if project["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(LIMITED_FUNCTIONS[project["project"].type])
        if recursive_subfolders:
            logger.info(
                "When using recursive subfolder parsing same name annotations in different "
                "subfolders will overwrite each other.",
            )
        logger.info(
            "The JSON files should follow a specific naming convention, matching file names already present "
            "on the platform. Existing annotations will be overwritten"
        )
        annotation_paths = get_annotation_paths(
            folder_path, from_s3_bucket, recursive_subfolders
        )
        logger.info(
            f"Uploading {len(annotation_paths)} annotations from {folder_path} to the project {project_folder_name}."
        )
        response = self.controller.upload_annotations_from_folder(
            project_name=project_name,
            folder_name=folder_name,
            annotation_paths=annotation_paths,  # noqa: E203
            client_s3_bucket=from_s3_bucket,
            folder_path=folder_path,
            is_pre_annotations=True,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_image_annotations(
        self,
        project: Union[NotEmptyStr, dict],
        image_name: str,
        annotation_json: Union[str, Path, dict],
        mask: Optional[Union[str, Path, bytes]] = None,
        verbose: Optional[StrictBool] = True,
    ):
        """Upload annotations from JSON (also mask for pixel annotations)
        to the image.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param annotation_json: annotations in SuperAnnotate format JSON dict or path to JSON file
        :type annotation_json: dict or Path-like (str or Path)
        :param mask: BytesIO object or filepath to mask annotation for pixel projects in SuperAnnotate format
        :type mask: BytesIO or Path-like (str or Path)
        """

        project_name, folder_name = extract_project_folder(project)

        project = self.controller.get_project_metadata(project_name).data
        if project["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(LIMITED_FUNCTIONS[project["project"].type])

        if not mask:
            if not isinstance(annotation_json, dict):
                mask_path = str(annotation_json).replace("___pixel.json", "___save.png")
            else:
                mask_path = f"{image_name}___save.png"
            if os.path.exists(mask_path):
                mask = open(mask_path, "rb").read()
        elif isinstance(mask, str) or isinstance(mask, Path):
            if os.path.exists(mask):
                mask = open(mask, "rb").read()

        if not isinstance(annotation_json, dict):
            if verbose:
                logger.info("Uploading annotations from %s.", annotation_json)
            annotation_json = json.load(open(annotation_json))
        response = self.controller.upload_image_annotations(
            project_name=project_name,
            folder_name=folder_name,
            image_name=image_name,
            annotations=annotation_json,
            mask=mask,
            verbose=verbose,
        )
        if response.errors and not response.errors == constants.INVALID_JSON_MESSAGE:
            raise AppException(response.errors)

    def download_model(self, model: MLModel, output_dir: Union[str, Path]):
        """Downloads the neural network and related files
        which are the <model_name>.pth/pkl. <model_name>.json, <model_name>.yaml, classes_mapper.json

        :param model: the model that needs to be downloaded
        :type  model: dict
        :param output_dir: the directiory in which the files will be saved
        :type output_dir: str
        :return: the metadata of the model
        :rtype: dict
        """
        res = self.controller.download_ml_model(
            model_data=model.dict(), download_path=output_dir
        )
        if res.errors:
            logger.error("\n".join([str(error) for error in res.errors]))
        else:
            return BaseSerializer(res.data).serialize()

    def benchmark(
        self,
        project: Union[NotEmptyStr, dict],
        gt_folder: str,
        folder_names: List[NotEmptyStr],
        export_root: Optional[Union[str, Path]] = None,
        image_list=None,
        annot_type: Optional[AnnotationType] = "bbox",
        show_plots=False,
    ):
        """Computes benchmark score for each instance of given images that are present both gt_project_name project and projects in folder_names list:

        :param project: project name or metadata of the project
        :type project: str or dict
        :param gt_folder: project folder name that contains the ground truth annotations
        :type gt_folder: str
        :param folder_names: list of folder names in the project for which the scores will be computed
        :type folder_names: list of str
        :param export_root: root export path of the projects
        :type export_root: Path-like (str or Path)
        :param image_list: List of image names from the projects list that must be used. If None, then all images from the projects list will be used. Default: None
        :type image_list: list
        :param annot_type: Type of annotation instances to consider. Available candidates are: ["bbox", "polygon", "point"]
        :type annot_type: str
        :param show_plots: If True, show plots based on results of consensus computation. Default: False
        :type show_plots: bool

        :return: Pandas DateFrame with columns (creatorEmail, QA, imageName, instanceId, className, area, attribute, folderName, score)
        :rtype: pandas DataFrame
        """
        project_name = project
        if isinstance(project, dict):
            project_name = project["name"]

        project = self.controller.get_project_metadata(project_name).data
        if project["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(LIMITED_FUNCTIONS[project["project"].type])

        if not export_root:
            with tempfile.TemporaryDirectory() as temp_dir:
                response = self.controller.benchmark(
                    project_name=project_name,
                    ground_truth_folder_name=gt_folder,
                    folder_names=folder_names,
                    export_root=temp_dir,
                    image_list=image_list,
                    annot_type=annot_type,
                    show_plots=show_plots,
                )

        else:
            response = self.controller.benchmark(
                project_name=project_name,
                ground_truth_folder_name=gt_folder,
                folder_names=folder_names,
                export_root=export_root,
                image_list=image_list,
                annot_type=annot_type,
                show_plots=show_plots,
            )
            if response.errors:
                raise AppException(response.errors)
        return response.data

    def consensus(
        self,
        project: NotEmptyStr,
        folder_names: List[NotEmptyStr],
        export_root: Optional[Union[NotEmptyStr, Path]] = None,
        image_list: Optional[List[NotEmptyStr]] = None,
        annot_type: Optional[AnnotationType] = "bbox",
        show_plots: Optional[StrictBool] = False,
    ):
        """Computes consensus score for each instance of given images that are present in at least 2 of the given projects:

        :param project: project name
        :type project: str
        :param folder_names: list of folder names in the project for which the scores will be computed
        :type folder_names: list of str
        :param export_root: root export path of the projects
        :type export_root: Path-like (str or Path)
        :param image_list: List of image names from the projects list that must be used. If None, then all images from the projects list will be used. Default: None
        :type image_list: list
        :param annot_type: Type of annotation instances to consider. Available candidates are: ["bbox", "polygon", "point"]
        :type annot_type: str
        :param show_plots: If True, show plots based on results of consensus computation. Default: False
        :type show_plots: bool

        :return: Pandas DateFrame with columns (creatorEmail, QA, imageName, instanceId, className, area, attribute, folderName, score)
        :rtype: pandas DataFrame
        """

        if export_root is None:
            with tempfile.TemporaryDirectory() as temp_dir:
                export_root = temp_dir
                response = self.controller.consensus(
                    project_name=project,
                    folder_names=folder_names,
                    export_path=export_root,
                    image_list=image_list,
                    annot_type=annot_type,
                    show_plots=show_plots,
                )

        else:
            response = self.controller.consensus(
                project_name=project,
                folder_names=folder_names,
                export_path=export_root,
                image_list=image_list,
                annot_type=annot_type,
                show_plots=show_plots,
            )
            if response.errors:
                raise AppException(response.errors)
        return response.data

    def run_prediction(
        self,
        project: Union[NotEmptyStr, dict],
        images_list: List[NotEmptyStr],
        model: Union[NotEmptyStr, dict],
    ):
        """This function runs smart prediction on given list of images from a given project using the neural network of your choice

        :param project: the project in which the target images are uploaded.
        :type project: str or dict
        :param images_list: the list of image names on which smart prediction has to be run
        :type images_list: list of str
        :param model: the name of the model that should be used for running smart prediction
        :type model: str or dict
        :return: tupe of two lists, list of images on which the prediction has succeded and failed respectively
        :rtype: tuple
        """
        project_name = None
        folder_name = None
        if isinstance(project, dict):
            project_name = project["name"]
        if isinstance(project, str):
            project_name, folder_name = extract_project_folder(project)

        model_name = model
        if isinstance(model, dict):
            model_name = model["name"]

        response = self.controller.run_prediction(
            project_name=project_name,
            images_list=images_list,
            model_name=model_name,
            folder_name=folder_name,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def add_annotation_bbox_to_image(
        self,
        project: NotEmptyStr,
        image_name: NotEmptyStr,
        bbox: List[float],
        annotation_class_name: NotEmptyStr,
        annotation_class_attributes: Optional[List[dict]] = None,
        error: Optional[StrictBool] = None,
    ):
        """Add a bounding box annotation to image annotations

        annotation_class_attributes has the form
        [ {"name" : "<attribute_value>" }, "groupName" : "<attribute_group>"} ], ... ]

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param bbox: 4 element list of top-left x,y and bottom-right x, y coordinates
        :type bbox: list of floats
        :param annotation_class_name: annotation class name
        :type annotation_class_name: str
        :param annotation_class_attributes: list of annotation class attributes
        :type annotation_class_attributes: list of 2 element dicts
        :param error: if not None, marks annotation as error (True) or no-error (False)
        :type error: bool
        """
        project_name, folder_name = extract_project_folder(project)
        project = self.controller.get_project_metadata(project_name).data
        if project["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(LIMITED_FUNCTIONS[project["project"].type])
        response = self.controller.get_annotations(
            project_name=project_name,
            folder_name=folder_name,
            item_names=[image_name],
            logging=False,
        )
        if response.errors:
            raise AppException(response.errors)
        if response.data:
            annotations = response.data[0]
        else:
            annotations = {}
        annotations = add_annotation_bbox_to_json(
            annotations,
            bbox,
            annotation_class_name,
            annotation_class_attributes,
            error,
            image_name,
        )

        self.controller.upload_image_annotations(
            project_name, folder_name, image_name, annotations
        )

    def add_annotation_point_to_image(
        self,
        project: NotEmptyStr,
        image_name: NotEmptyStr,
        point: List[float],
        annotation_class_name: NotEmptyStr,
        annotation_class_attributes: Optional[List[dict]] = None,
        error: Optional[StrictBool] = None,
    ):
        """Add a point annotation to image annotations

        annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param point: [x,y] list of coordinates
        :type point: list of floats
        :param annotation_class_name: annotation class name
        :type annotation_class_name: str
        :param annotation_class_attributes: list of annotation class attributes
        :type annotation_class_attributes: list of 2 element dicts
        :param error: if not None, marks annotation as error (True) or no-error (False)
        :type error: bool
        """
        project_name, folder_name = extract_project_folder(project)
        project = self.controller.get_project_metadata(project_name).data
        if project["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(LIMITED_FUNCTIONS[project["project"].type])
        response = self.controller.get_annotations(
            project_name=project_name,
            folder_name=folder_name,
            item_names=[image_name],
            logging=False,
        )
        if response.errors:
            raise AppException(response.errors)
        if response.data:
            annotations = response.data[0]
        else:
            annotations = {}
        annotations = add_annotation_point_to_json(
            annotations,
            point,
            annotation_class_name,
            image_name,
            annotation_class_attributes,
            error,
        )
        self.controller.upload_image_annotations(
            project_name, folder_name, image_name, annotations
        )

    def add_annotation_comment_to_image(
        self,
        project: NotEmptyStr,
        image_name: NotEmptyStr,
        comment_text: NotEmptyStr,
        comment_coords: List[float],
        comment_author: EmailStr,
        resolved: Optional[StrictBool] = False,
    ):
        """Add a comment to SuperAnnotate format annotation JSON

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param image_name: image name
        :type image_name: str
        :param comment_text: comment text
        :type comment_text: str
        :param comment_coords: [x, y] coords
        :type comment_coords: list
        :param comment_author: comment author email
        :type comment_author: str
        :param resolved: comment resolve status
        :type resolved: bool
        """
        project_name, folder_name = extract_project_folder(project)
        project = self.controller.get_project_metadata(project_name).data
        if project["project"].type in [
            constants.ProjectType.VIDEO.value,
            constants.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(LIMITED_FUNCTIONS[project["project"].type])
        response = self.controller.get_annotations(
            project_name=project_name,
            folder_name=folder_name,
            item_names=[image_name],
            logging=False,
        )
        if response.errors:
            raise AppException(response.errors)
        if response.data:
            annotations = response.data[0]
        else:
            annotations = {}
        annotations = add_annotation_comment_to_json(
            annotations,
            comment_text,
            comment_coords,
            comment_author,
            resolved=resolved,
            image_name=image_name,
        )
        self.controller.upload_image_annotations(
            project_name, folder_name, image_name, annotations
        )

    def upload_image_to_project(
        self,
        project: NotEmptyStr,
        img,
        image_name: Optional[NotEmptyStr] = None,
        annotation_status: Optional[AnnotationStatuses] = "NotStarted",
        from_s3_bucket=None,
        image_quality_in_editor: Optional[NotEmptyStr] = None,
    ):
        """Uploads image (io.BytesIO() or filepath to image) to project.
        Sets status of the uploaded image to set_status if it is not None.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param img: image to upload
        :type img: io.BytesIO() or Path-like (str or Path)
        :param image_name: image name to set on platform. If None and img is filepath,
                           image name will be set to filename of the path
        :type image_name: str
        :param annotation_status: value to set the annotation statuses of the uploaded image NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_status: str
        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str
        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
               Can be either "compressed" or "original".  If None then the default value in project settings will be used.
        :type image_quality_in_editor: str
        """
        project_name, folder_name = extract_project_folder(project)

        response = self.controller.upload_image_to_project(
            project_name=project_name,
            folder_name=folder_name,
            image_name=image_name,
            image=img,
            annotation_status=annotation_status,
            from_s3_bucket=from_s3_bucket,
            image_quality_in_editor=image_quality_in_editor,
        )
        if response.errors:
            raise AppException(response.errors)

    def search_models(
        self,
        name: Optional[NotEmptyStr] = None,
        type_: Optional[NotEmptyStr] = None,
        project_id: Optional[int] = None,
        task: Optional[NotEmptyStr] = None,
        include_global: Optional[StrictBool] = True,
    ):
        """Search for ML models.

        :param name: search string
        :type name: str
        :param type_: ml model type string
        :type type_: str
        :param project_id: project id
        :type project_id: int
        :param task: training task
        :type task: str
        :param include_global: include global ml models
        :type include_global: bool

            :return: ml model metadata
            :rtype: list of dicts
        """
        res = self.controller.search_models(
            name=name,
            model_type=type_,
            project_id=project_id,
            task=task,
            include_global=include_global,
        )
        return res.data

    def upload_images_to_project(
        self,
        project: NotEmptyStr,
        img_paths: List[NotEmptyStr],
        annotation_status: Optional[AnnotationStatuses] = "NotStarted",
        from_s3_bucket=None,
        image_quality_in_editor: Optional[ImageQualityChoices] = None,
    ):
        """Uploads all images given in list of path objects in img_paths to the project.
        Sets status of all the uploaded images to set_status if it is not None.

        If an image with existing name already exists in the project it won't be uploaded,
        and its path will be appended to the third member of return value of this
        function.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param img_paths: list of Path-like (str or Path) objects to upload
        :type img_paths: list
        :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
        :type annotation_status: str
        :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
        :type from_s3_bucket: str
        :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
               Can be either "compressed" or "original".  If None then the default value in project settings will be used.
        :type image_quality_in_editor: str

        :return: uploaded, could-not-upload, existing-images filepaths
        :rtype: tuple (3 members) of list of strs
        """
        project_name, folder_name = extract_project_folder(project)

        use_case = self.controller.upload_images_to_project(
            project_name=project_name,
            folder_name=folder_name,
            paths=img_paths,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
            from_s3_bucket=from_s3_bucket,
        )

        images_to_upload, duplicates = use_case.images_to_upload
        if len(duplicates):
            logger.warning(
                "%s already existing images found that won't be uploaded.",
                len(duplicates),
            )
        logger.info(f"Uploading {len(images_to_upload)} images to project {project}.")
        uploaded, failed_images, duplications = [], [], duplicates
        if not images_to_upload:
            return uploaded, failed_images, duplications
        if use_case.is_valid():
            with tqdm(
                total=len(images_to_upload), desc="Uploading images"
            ) as progress_bar:
                for _ in use_case.execute():
                    progress_bar.update(1)
            uploaded, failed_images, duplications = use_case.data
            if duplications:
                logger.info(f"Duplicated images {', '.join(duplications)}")
            return uploaded, failed_images, duplications
        raise AppException(use_case.response.errors)

    def aggregate_annotations_as_df(
        self,
        project_root: Union[NotEmptyStr, Path],
        project_type: ProjectTypes,
        folder_names: Optional[List[Union[Path, NotEmptyStr]]] = None,
    ):
        """Aggregate annotations as pandas dataframe from project root.

        :param project_root: the export path of the project
        :type project_root: Path-like (str or Path)

        :param project_type: the project type, Vector/Pixel, Video or Document
        :type project_type: str

        :param folder_names: Aggregate the specified folders from project_root.
         If None aggregate all folders in the project_root
        :type folder_names: list of Pathlike (str or Path) objects

        :return: DataFrame on annotations
        :rtype: pandas DataFrame
        """
        if project_type in (
            constants.ProjectType.VECTOR.name,
            constants.ProjectType.PIXEL.name,
        ):
            from superannotate.lib.app.analytics.common import (
                aggregate_image_annotations_as_df,
            )

            return aggregate_image_annotations_as_df(
                project_root=project_root,
                include_classes_wo_annotations=False,
                include_comments=True,
                include_tags=True,
                folder_names=folder_names,
            )
        elif project_type in (
            constants.ProjectType.VIDEO.name,
            constants.ProjectType.DOCUMENT.name,
        ):
            from superannotate.lib.app.analytics.aggregators import DataAggregator

            return DataAggregator(
                project_type=project_type,
                project_root=project_root,
                folder_names=folder_names,
            ).aggregate_annotations_as_df()

    def delete_annotations(
        self, project: NotEmptyStr, item_names: Optional[List[NotEmptyStr]] = None
    ):
        """
        Delete item annotations from a given list of items.

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
        :param item_names:  image names. If None, all image annotations from a given project/folder will be deleted.
        :type item_names: list of strs
        """

        project_name, folder_name = extract_project_folder(project)

        response = self.controller.delete_annotations(
            project_name=project_name, folder_name=folder_name, item_names=item_names
        )
        if response.errors:
            raise AppException(response.errors)

    def validate_annotations(
        self, project_type: ProjectTypes, annotations_json: Union[NotEmptyStr, Path]
    ):
        """Validates given annotation JSON.

        :param project_type: The project type Vector, Pixel, Video or Document
        :type project_type: str

        :param annotations_json: path to annotation JSON
        :type annotations_json: Path-like (str or Path)

        :return: The success of the validation
        :rtype: bool
        """
        with open(annotations_json) as file:
            annotation_data = json.loads(file.read())
            response = Controller.validate_annotations(
                project_type, annotation_data, allow_extra=False
            )
            if response.errors:
                raise AppException(response.errors)
            is_valid, _ = response.data
            if is_valid:
                return True
            print(response.report)
            return False

    def add_contributors_to_project(
        self,
        project: NotEmptyStr,
        emails: conlist(EmailStr, min_items=1),
        role: AnnotatorRole,
    ) -> Tuple[List[str], List[str]]:
        """Add contributors to project.

        :param project: project name
        :type project: str

        :param emails: users email
        :type emails: list

        :param role: user role to apply, one of Admin , Annotator , QA
        :type role: str

        :return: lists of added,  skipped contributors of the project
        :rtype: tuple (2 members) of lists of strs
        """
        response = self.controller.add_contributors_to_project(
            project_name=project, emails=emails, role=role
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def invite_contributors_to_team(
        self, emails: conlist(EmailStr, min_items=1), admin: StrictBool = False
    ) -> Tuple[List[str], List[str]]:
        """Invites contributors to the team.

        :param emails: list of contributor emails
        :type emails: list

        :param admin: enables admin privileges for the contributor
        :type admin: bool

        :return: lists of invited, skipped contributors of the team
        :rtype: tuple (2 members) of lists of strs
        """
        response = self.controller.invite_contributors_to_team(
            emails=emails, set_admin=admin
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_annotations(
        self, project: NotEmptyStr, items: Optional[List[NotEmptyStr]] = None
    ):
        """Returns annotations for the given list of items.

        :param project: project name or folder path (e.g., “project1/folder1”).
        :type project: str

        :param items:  item names. If None all items in the project will be exported
        :type items: list of strs

        :return: list of annotations
        :rtype: list of strs
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.get_annotations(project_name, folder_name, items)
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_annotations_per_frame(
        self, project: NotEmptyStr, video: NotEmptyStr, fps: int = 1
    ):
        """Returns per frame annotations for the given video.


        :param project: project name or folder path (e.g., “project1/folder1”).
        :type project: str

        :param video: video name
        :type video: str

        :param fps: how many frames per second needs to be extracted from the video.
         Will extract 1 frame per second by default.
        :type fps: str

        :return: list of annotation objects
        :rtype: list of dicts
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.get_annotations_per_frame(
            project_name, folder_name, video_name=video, fps=fps
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def upload_priority_scores(self, project: NotEmptyStr, scores: List[PriorityScore]):
        """Returns per frame annotations for the given video.

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param scores: list of score objects
        :type scores: list of dicts

        :return: lists of uploaded, skipped items
        :rtype: tuple (2 members) of lists of strs
        """
        project_name, folder_name = extract_project_folder(project)
        project_folder_name = project
        response = self.controller.upload_priority_scores(
            project_name, folder_name, scores, project_folder_name
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_integrations(self):
        """Get all integrations per team

        :return: metadata objects of all integrations of the team.
        :rtype: list of dicts
        """
        response = self.controller.get_integrations()
        if response.errors:
            raise AppException(response.errors)
        integrations = response.data
        return BaseSerializer.serialize_iterable(integrations, ("name", "type", "root"))

    def attach_items_from_integrated_storage(
        self,
        project: NotEmptyStr,
        integration: Union[NotEmptyStr, IntegrationEntity],
        folder_path: Optional[NotEmptyStr] = None,
    ):
        """Link images from integrated external storage to SuperAnnotate.

        :param project: project name or folder path where items should be attached (e.g., “project1/folder1”).
        :type project: str

        :param integration:  existing integration name or metadata dict to pull items from.
         Mandatory keys in integration metadata’s dict is “name”.
        :type integration: str or dict

        :param folder_path: Points to an exact folder/directory within given storage.
         If None, items     are fetched from the root directory.
        :type folder_path: str
        """
        project_name, folder_name = extract_project_folder(project)
        if isinstance(integration, str):
            integration = IntegrationEntity(name=integration)
        response = self.controller.attach_integrations(
            project_name, folder_name, integration, folder_path
        )
        if response.errors:
            raise AppException(response.errors)

    def query(self, project: NotEmptyStr, query: Optional[NotEmptyStr]):
        """Return items that satisfy the given query.
        Query syntax should be in SuperAnnotate query language(https://doc.superannotate.com/docs/query-search-1).

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param query: SAQuL query string.
        :type query: str

        :return: queried items’ metadata list
        :rtype: list of dicts
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.query_entities(project_name, folder_name, query)
        if response.errors:
            raise AppException(response.errors)
        return BaseSerializer.serialize_iterable(response.data)

    def get_item_metadata(
        self,
        project: NotEmptyStr,
        item_name: NotEmptyStr,
    ):
        """Returns item metadata

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param item_name: item name
        :type item_name: str

        :return: metadata of item
        :rtype: dict
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.get_item(project_name, folder_name, item_name)
        if response.errors:
            raise AppException(response.errors)
        return BaseSerializer(response.data).serialize()

    def search_items(
        self,
        project: NotEmptyStr,
        name_contains: NotEmptyStr = None,
        annotation_status: Optional[AnnotationStatuses] = None,
        annotator_email: Optional[NotEmptyStr] = None,
        qa_email: Optional[NotEmptyStr] = None,
        recursive: bool = False,
    ):
        """Search items by filtering criteria.


        :param project: project name or folder path (e.g., “project1/folder1”).
         If recursive=False=True, then only the project name is required.
        :type project: str

        :param name_contains:  Returns those items, where the given string is found anywhere within an item’s name.
         If None, all items returned, in accordance with the recursive=False parameter.
        :type name_contains: str

        :param annotation_status: if not None, filters items by annotation status.
                            Values are:
                                ♦ “NotStarted” \n
                                ♦ “InProgress” \n
                                ♦ “QualityCheck” \n
                                ♦ “Returned” \n
                                ♦ “Completed” \n
                                ♦ “Skippe
        :type annotation_status: str
        :type annotation_status: str


        :param annotator_email: returns those items’ names that are assigned to the specified annotator.
         If None, all items are returned. Strict equal.
        :type annotator_email: str

        :param qa_email:  returns those items’ names that are assigned to the specified QA.
         If None, all items are returned. Strict equal.
        :type qa_email: str

        :param recursive: search in the project’s root and all of its folders.
         If False search only in the project’s root or given directory.
        :type recursive: bool

        :return: items' metadata
        :rtype: list of dicts
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.list_items(
            project_name,
            folder_name,
            name_contains=name_contains,
            annotation_status=annotation_status,
            annotator_email=annotator_email,
            qa_email=qa_email,
            recursive=recursive,
        )
        if response.errors:
            raise AppException(response.errors)
        return BaseSerializer.serialize_iterable(response.data)

    def attach_items(
        self,
        project: Union[NotEmptyStr, dict],
        attachments: AttachmentArg,
        annotation_status: Optional[AnnotationStatuses] = "NotStarted",
    ):
        """Link items from external storage to SuperAnnotate using URLs.

        :param project: project name or folder path (e.g., “project1/folder1”)
        :type project: str

        :param attachments: path to CSV file or list of dicts containing attachments URLs.
        :type attachments: path-like (str or Path) or list of dicts

        :param annotation_status: value to set the annotation statuses of the linked items
                                   “NotStarted”
                                   “InProgress”
                                   “QualityCheck”
                                   “Returned”
                                   “Completed”
                                   “Skipped”
        :type annotation_status: str
        """
        attachments = attachments.data
        project_name, folder_name = extract_project_folder(project)
        if attachments and isinstance(attachments[0], AttachmentDict):
            unique_attachments = set(attachments)
            duplicate_attachments = [
                item
                for item, count in collections.Counter(attachments).items()
                if count > 1
            ]
        else:
            (
                unique_attachments,
                duplicate_attachments,
            ) = get_name_url_duplicated_from_csv(attachments)
        if duplicate_attachments:
            logger.info("Dropping duplicates.")
        unique_attachments = parse_obj_as(List[AttachmentEntity], unique_attachments)
        uploaded, fails, duplicated = [], [], []
        if unique_attachments:
            logger.info(
                f"Attaching {len(unique_attachments)} file(s) to project {project}."
            )
            response = self.controller.attach_items(
                project_name=project_name,
                folder_name=folder_name,
                attachments=unique_attachments,
                annotation_status=annotation_status,
            )
            if response.errors:
                raise AppException(response.errors)
            uploaded, duplicated = response.data
            uploaded = [i["name"] for i in uploaded]
            fails = [
                attachment.name
                for attachment in unique_attachments
                if attachment.name not in uploaded and attachment.name not in duplicated
            ]
        return uploaded, fails, duplicated

    def copy_items(
        self,
        source: Union[NotEmptyStr, dict],
        destination: Union[NotEmptyStr, dict],
        items: Optional[List[NotEmptyStr]] = None,
        include_annotations: Optional[StrictBool] = True,
    ):
        """Copy images in bulk between folders in a project

        :param source: project name or folder path to select items from (e.g., “project1/folder1”).
        :type source: str

        :param destination: project name (root) or folder path to place copied items.
        :type destination: str

        :param items: names of items to copy. If None, all items from the source directory will be copied.
        :type items: list of str

        :param include_annotations: enables annotations copy
        :type include_annotations: bool

        :return: list of skipped item names
        :rtype: list of strs
        """

        project_name, source_folder = extract_project_folder(source)

        to_project_name, destination_folder = extract_project_folder(destination)
        if project_name != to_project_name:
            raise AppException("Source and destination projects should be the same")

        response = self.controller.copy_items(
            project_name=project_name,
            from_folder=source_folder,
            to_folder=destination_folder,
            items=items,
            include_annotations=include_annotations,
        )
        if response.errors:
            raise AppException(response.errors)

        return response.data

    def move_items(
        self,
        source: Union[NotEmptyStr, dict],
        destination: Union[NotEmptyStr, dict],
        items: Optional[List[NotEmptyStr]] = None,
    ):
        """Move images in bulk between folders in a project

        :param source: project name or folder path to pick items from (e.g., “project1/folder1”).
        :type source: str

        :param destination: project name (root) or folder path to move items to.
        :type destination: str

        :param items: names of items to move. If None, all items from the source directory will be moved.
        :type items: list of str

        :return: list of skipped item names
        :rtype: list of strs
        """

        project_name, source_folder = extract_project_folder(source)
        to_project_name, destination_folder = extract_project_folder(destination)
        if project_name != to_project_name:
            raise AppException("Source and destination projects should be the same")
        response = self.controller.move_items(
            project_name=project_name,
            from_folder=source_folder,
            to_folder=destination_folder,
            items=items,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def set_annotation_statuses(
        self,
        project: Union[NotEmptyStr, dict],
        annotation_status: AnnotationStatuses,
        item_names: Optional[List[NotEmptyStr]] = None,
    ):
        """Sets annotation statuses of items

        :param project: project name or folder path (e.g., “project1/folder1”).
        :type project: str

        :param annotation_status: annotation status to set, should be one of.
                                    “NotStarted”
                                    “InProgress”
                                    “QualityCheck”
                                    “Returned”
                                    “Completed”
                                    “Skipped”
        :type annotation_status: str

        :param items:  item names to set the mentioned status for. If None, all the items in the project will be used.
        :type items: str
        """

        project_name, folder_name = extract_project_folder(project)
        response = self.controller.set_annotation_statuses(
            project_name=project_name,
            folder_name=folder_name,
            annotation_status=annotation_status,
            item_names=item_names,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def download_annotations(
        self,
        project: Union[NotEmptyStr, dict],
        path: Union[str, Path] = None,
        items: Optional[List[NotEmptyStr]] = None,
        recursive: bool = False,
        callback: Callable = None,
    ):
        """Downloads annotation JSON files of the selected items to the local directory.

        :param project: project name or folder path (e.g., “project1/folder1”).
        :type project: str

        :param path:  local directory path where the annotations will be downloaded. If none, the current directory is used.
        :type path: Path-like (str or Path)

        :param items: project name (root) or folder path to move items to.
        :type items: list of str

        :param recursive: download annotations from the project’s root and all of its folders with the preserved structure.
         If False download only from the project’s root or given directory.
        :type recursive: bool

        :param callback: a function that allows you to modify each annotation’s dict before downloading.
         The function receives each annotation as an argument and the returned value will be applied to the download.
        :type callback: callable

        :return: local path of the downloaded annotations folder.
        :rtype: str
        """
        project_name, folder_name = extract_project_folder(project)
        response = self.controller.download_annotations(
            project_name=project_name,
            folder_name=folder_name,
            destination=path,
            recursive=recursive,
            item_names=items,
            callback=callback,
        )
        if response.errors:
            raise AppException(response.errors)
        return response.data
