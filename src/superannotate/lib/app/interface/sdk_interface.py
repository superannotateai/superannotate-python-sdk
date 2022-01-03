import io
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import boto3
import lib.core as constances
from lib.app.annotation_helpers import add_annotation_bbox_to_json
from lib.app.annotation_helpers import add_annotation_comment_to_json
from lib.app.annotation_helpers import add_annotation_point_to_json
from lib.app.helpers import extract_project_folder
from lib.app.helpers import get_annotation_paths
from lib.app.helpers import get_paths_and_duplicated_from_csv
from lib.app.interface.types import AnnotationStatuses
from lib.app.interface.types import AnnotationType
from lib.app.interface.types import AnnotatorRole
from lib.app.interface.types import EmailStr
from lib.app.interface.types import ImageQualityChoices
from lib.app.interface.types import NotEmptyStr
from lib.app.interface.types import ProjectTypes
from lib.app.interface.types import validate_arguments
from lib.app.mixp.decorators import Trackable
from lib.app.serializers import BaseSerializers
from lib.app.serializers import ImageSerializer
from lib.app.serializers import ProjectSerializer
from lib.app.serializers import SettingsSerializer
from lib.app.serializers import TeamSerializer
from lib.core import LIMITED_FUNCTIONS
from lib.core.enums import ImageQuality
from lib.core.exceptions import AppException
from lib.core.plugin import VideoPlugin
from lib.core.types import AttributeGroup
from lib.core.types import ClassesJson
from lib.core.types import MLModel
from lib.core.types import Project
from lib.infrastructure.controller import Controller
from pydantic import conlist
from pydantic import parse_obj_as
from pydantic import StrictBool
from tqdm import tqdm


controller = Controller.get_instance()
logger = logging.getLogger("root")


@validate_arguments
def init(path_to_config_json: Optional[str] = None):
    """
    Initializes and authenticates to SuperAnnotate platform using the config file.
    If not initialized then $HOME/.superannotate/config.json
    will be used.

    :param path_to_config_json: Location to config JSON file
    :type path_to_config_json: str or Path
    """
    global controller
    controller.init(path_to_config_json)


@validate_arguments
def set_auth_token(token: str):
    controller.set_token(token)


@Trackable
def get_team_metadata():

    """Returns team metadata

    :return: team metadata
    :rtype: dict
    """
    response = controller.get_team()
    return TeamSerializer(response.data).serialize()


@Trackable
@validate_arguments
def search_team_contributors(
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

    contributors = controller.search_team_contributors(
        email=email, first_name=first_name, last_name=last_name
    ).data
    if not return_metadata:
        return [contributor["email"] for contributor in contributors]
    return contributors


@Trackable
@validate_arguments
def search_projects(
    name: Optional[NotEmptyStr] = None,
    return_metadata: bool = False,
    include_complete_image_count: bool = False,
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

    :return: project names or metadatas
    :rtype: list of strs or dicts
    """
    result = controller.search_project(
        name=name, include_complete_image_count=include_complete_image_count
    ).data
    if return_metadata:
        return [ProjectSerializer(project).serialize() for project in result]
    else:
        return [project.name for project in result]


@Trackable
@validate_arguments
def create_project(
    project_name: NotEmptyStr,
    project_description: NotEmptyStr,
    project_type: NotEmptyStr,
):
    """Create a new project in the team.

    :param project_name: the new project's name
    :type project_name: str
    :param project_description: the new project's description
    :type project_description: str
    :param project_type: the new project type, Vector or Pixel.
    :type project_type: str

    :return: dict object metadata the new project
    :rtype: dict
    """
    response = controller.create_project(
        name=project_name, description=project_description, project_type=project_type
    )
    if response.errors:
        raise AppException(response.errors)

    return ProjectSerializer(response.data).serialize()


@Trackable
@validate_arguments
def create_project_from_metadata(project_metadata: Project):
    """Create a new project in the team using project metadata object dict.
    Mandatory keys in project_metadata are "name", "description" and "type" (Vector or Pixel)
    Non-mandatory keys: "workflow", "contributors", "settings" and "annotation_classes".

    :return: dict object metadata the new project
    :rtype: dict
    """
    project_metadata = project_metadata.dict()
    response = controller.create_project(
        name=project_metadata["name"],
        description=project_metadata["description"],
        project_type=project_metadata["type"],
        contributors=project_metadata.get("contributors", []),
        settings=project_metadata.get("settings", []),
        annotation_classes=project_metadata.get("classes", []),
        workflows=project_metadata.get("workflow", []),
    )
    if response.errors:
        raise AppException(response.errors)
    return ProjectSerializer(response.data).serialize()


@Trackable
@validate_arguments
def clone_project(
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
    response = controller.clone_project(
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


@Trackable
@validate_arguments
def search_images(
    project: Union[NotEmptyStr, dict],
    image_name_prefix: Optional[NotEmptyStr] = None,
    annotation_status: Optional[AnnotationStatuses] = None,
    return_metadata: Optional[StrictBool] = False,
):
    """Search images by name_prefix (case-insensitive) and annotation status

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name_prefix: image name prefix for search
    :type image_name_prefix: str
    :param annotation_status: if not None, annotation statuses of images to filter,
                              should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :param return_metadata: return metadata of images instead of names
    :type return_metadata: bool

    :return: metadata of found images or image names
    :rtype: list of dicts or strs
    """

    project_name, folder_name = extract_project_folder(project)
    project = controller._get_project(project_name)

    response = controller.search_images(
        project_name=project_name,
        folder_path=folder_name,
        annotation_status=annotation_status,
        image_name_prefix=image_name_prefix,
    )
    if response.errors:
        raise AppException(response.errors)

    if return_metadata:
        return [
            ImageSerializer(image).serialize_by_project(project)
            for image in response.data
        ]
    return [image.name for image in response.data]


@Trackable
@validate_arguments
def create_folder(project: NotEmptyStr, folder_name: NotEmptyStr):
    """Create a new folder in the project.

    :param project: project name
    :type project: str
    :param folder_name: the new folder's name
    :type folder_name: str

    :return: dict object metadata the new folder
    :rtype: dict
    """

    res = controller.create_folder(project=project, folder_name=folder_name)
    if res.data:
        folder = res.data
        logger.info(f"Folder {folder.name} created in project {project}")
        return folder.to_dict()
    if res.errors:
        raise AppException(res.errors)


@Trackable
@validate_arguments
def delete_project(project: Union[NotEmptyStr, dict]):
    """Deletes the project

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
    """
    name = project
    if isinstance(project, dict):
        name = project["name"]
    controller.delete_project(name=name)


@Trackable
@validate_arguments
def rename_project(project: NotEmptyStr, new_name: NotEmptyStr):
    """Renames the project

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param new_name: project's new name
    :type new_name: str
    """

    response = controller.update_project(name=project, project_data={"name": new_name})
    if response.errors:
        raise AppException(response.errors)

    logger.info(
        "Successfully renamed project %s to %s.", project, response.data["name"]
    )


@Trackable
@validate_arguments
def get_folder_metadata(project: NotEmptyStr, folder_name: NotEmptyStr):
    """Returns folder metadata

    :param project: project name
    :type project: str
    :param folder_name: folder's name
    :type folder_name: str

    :return: metadata of folder
    :rtype: dict
    """
    result = controller.get_folder(project_name=project, folder_name=folder_name).data
    if not result:
        raise AppException("Folder not found.")
    return result.to_dict()


@Trackable
@validate_arguments
def delete_folders(project: NotEmptyStr, folder_names: List[NotEmptyStr]):
    """Delete folder in project.

    :param project: project name
    :type project: str
    :param folder_names: to be deleted folders' names
    :type folder_names: list of strs
    """

    res = controller.delete_folders(project_name=project, folder_names=folder_names)
    if res.errors:
        raise AppException(res.errors)
    logger.info(f"Folders {folder_names} deleted in project {project}")


@Trackable
@validate_arguments
def get_project_and_folder_metadata(project: Union[NotEmptyStr, dict]):
    """Returns project and folder metadata tuple. If folder part is empty,
    than returned folder part is set to None.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str

    :return: tuple of project and folder
    :rtype: tuple
    """
    project_name, folder_name = extract_project_folder(project)
    project = ProjectSerializer(
        controller.search_project(project_name).data[0]
    ).serialize()
    folder = None
    if folder_name:
        folder = get_folder_metadata(project_name, folder_name)
    return project, folder


@Trackable
@validate_arguments
def search_folders(
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

    response = controller.search_folders(
        project_name=project, folder_name=folder_name, include_users=return_metadata
    )
    if response.errors:
        raise AppException(response.errors)
    data = response.data
    if return_metadata:
        return [BaseSerializers(folder).serialize() for folder in data]
    return [folder.name for folder in data]


@Trackable
@validate_arguments
def copy_image(
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
    source_project_metadata = controller.get_project_metadata(source_project_name).data
    destination_project_metadata = controller.get_project_metadata(
        destination_project
    ).data

    if destination_project_metadata["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ] or source_project_metadata["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(
            LIMITED_FUNCTIONS[source_project_metadata["project"].project_type]
        )

    response = controller.copy_image(
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
        controller.copy_image_annotation_classes(
            from_project_name=source_project_name,
            from_folder_name=source_folder_name,
            to_folder_name=destination_folder,
            to_project_name=destination_project,
            image_name=image_name,
        )
    if copy_pin:
        controller.update_image(
            project_name=destination_project,
            folder_name=destination_folder,
            image_name=image_name,
            is_pinned=1,
        )
    logger.info(
        f"Copied image {source_project}/{image_name}"
        f" to {destination_project}/{destination_folder}."
    )


@Trackable
@validate_arguments
def upload_images_from_public_urls_to_project(
    project: Union[NotEmptyStr, dict],
    img_urls: List[NotEmptyStr],
    img_names: Optional[List[NotEmptyStr]] = None,
    annotation_status: Optional[AnnotationStatuses] = "NotStarted",
    image_quality_in_editor: Optional[NotEmptyStr] = None,
):
    """Uploads all images given in the list of URL strings in img_urls to the project.
    Sets status of all the uploaded images to annotation_status if it is not None.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param img_urls: list of str objects to upload
    :type img_urls: list
    :param img_names: list of str names for each urls in img_url list
    :type img_names: list
    :param annotation_status: value to set the annotation statuses of the uploaded images
     NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded images' urls, uploaded images' filenames, duplicate images' filenames
     and not-uploaded images' urls
    :rtype: tuple of list of strs
    """

    project_name, folder_name = extract_project_folder(project)

    use_case = controller.upload_images_from_public_urls_to_project(
        project_name=project_name,
        folder_name=folder_name,
        image_urls=img_urls,
        image_names=img_names,
        annotation_status=annotation_status,
        image_quality_in_editor=image_quality_in_editor,
    )
    if use_case.is_valid():
        with tqdm(total=len(img_urls), desc="Uploading images") as progress_bar:
            for _ in use_case.execute():
                progress_bar.update(1)
        return use_case.data
    raise AppException(use_case.response.errors)


@Trackable
@validate_arguments
def copy_images(
    source_project: Union[NotEmptyStr, dict],
    image_names: Optional[List[NotEmptyStr]],
    destination_project: Union[NotEmptyStr, dict],
    include_annotations: Optional[StrictBool] = True,
    copy_pin: Optional[StrictBool] = True,
):
    """Copy images in bulk between folders in a project

    :param source_project: project name or folder path (e.g., "project1/folder1")
    :type source_project: str`
    :param image_names: image names. If None, all images from source project will be copied
    :type image_names: list of str
    :param destination_project: project name or folder path (e.g., "project1/folder2")
    :type destination_project: str
    :param include_annotations: enables annotations copy
    :type include_annotations: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    :return: list of skipped image names
    :rtype: list of strs
    """

    project_name, source_folder_name = extract_project_folder(source_project)

    to_project_name, destination_folder_name = extract_project_folder(
        destination_project
    )
    if project_name != to_project_name:
        raise AppException(
            "Source and destination projects should be the same for copy_images"
        )
    if not image_names:
        images = controller.search_images(
            project_name=project_name, folder_path=source_folder_name
        ).data
        image_names = [image.name for image in images]

    res = controller.bulk_copy_images(
        project_name=project_name,
        from_folder_name=source_folder_name,
        to_folder_name=destination_folder_name,
        image_names=image_names,
        include_annotations=include_annotations,
        include_pin=copy_pin,
    )
    if res.errors:
        raise AppException(res.errors)
    skipped_images = res.data
    done_count = len(image_names) - len(skipped_images)
    message_postfix = "{from_path} to {to_path}."
    message_prefix = "Copied images from "
    if done_count > 1 or done_count == 0:
        message_prefix = f"Copied {done_count}/{len(image_names)} images from "
    elif done_count == 1:
        message_prefix = "Copied an image from "
    logger.info(
        message_prefix
        + message_postfix.format(from_path=source_project, to_path=destination_project)
    )

    return skipped_images


@Trackable
@validate_arguments
def move_images(
    source_project: Union[NotEmptyStr, dict],
    image_names: Optional[List[NotEmptyStr]],
    destination_project: Union[NotEmptyStr, dict],
    *args,
    **kwargs,
):
    """Move images in bulk between folders in a project

    :param source_project: project name or folder path (e.g., "project1/folder1")
    :type source_project: str
    :param image_names: image names. If None, all images from source project will be moved
    :type image_names: list of str
    :param destination_project: project name or folder path (e.g., "project1/folder2")
    :type destination_project: str
    :return: list of skipped image names
    :rtype: list of strs
    """
    project_name, source_folder_name = extract_project_folder(source_project)

    project = controller.get_project_metadata(project_name).data
    if project["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(LIMITED_FUNCTIONS[project["project"].project_type])

    to_project_name, destination_folder_name = extract_project_folder(
        destination_project
    )

    if project_name != to_project_name:
        raise AppException(
            "Source and destination projects should be the same for move_images"
        )

    if not image_names:
        images = controller.search_images(
            project_name=project_name, folder_path=source_folder_name
        )
        images = images.data
        image_names = [image.name for image in images]

    response = controller.bulk_move_images(
        project_name=project_name,
        from_folder_name=source_folder_name,
        to_folder_name=destination_folder_name,
        image_names=image_names,
    )
    if response.errors:
        raise AppException(response.errors)
    moved_images = response.data
    moved_count = len(moved_images)
    message_postfix = "{from_path} to {to_path}."
    message_prefix = "Moved images from "
    if moved_count > 1 or moved_count == 0:
        message_prefix = f"Moved {moved_count}/{len(image_names)} images from "
    elif moved_count == 1:
        message_prefix = "Moved an image from"

    logger.info(
        message_prefix
        + message_postfix.format(from_path=source_project, to_path=destination_project)
    )

    return list(set(image_names) - set(moved_images))


@Trackable
@validate_arguments
def get_project_metadata(
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

    :return: metadata of project
    :rtype: dict
    """
    project_name, folder_name = extract_project_folder(project)
    response = controller.get_project_metadata(
        project_name,
        include_annotation_classes,
        include_settings,
        include_workflow,
        include_contributors,
        include_complete_image_count,
    ).data

    metadata = ProjectSerializer(response["project"]).serialize()
    metadata["settings"] = [
        SettingsSerializer(setting).serialize()
        for setting in response.get("settings", [])
    ]

    for elem in "classes", "workflows", "contributors":
        if response.get(elem):
            metadata[elem] = [
                BaseSerializers(attribute).serialize() for attribute in response[elem]
            ]
        else:
            metadata[elem] = []
    return metadata


@Trackable
@validate_arguments
def get_project_settings(project: Union[NotEmptyStr, dict]):
    """Gets project's settings.

    Return value example: [{ "attribute" : "Brightness", "value" : 10, ...},...]

    :param project: project name or metadata
    :type project: str or dict

    :return: project settings
    :rtype: list of dicts
    """
    project_name, folder_name = extract_project_folder(project)
    settings = controller.get_project_settings(project_name=project_name)
    settings = [
        SettingsSerializer(attribute).serialize() for attribute in settings.data
    ]
    return settings


@Trackable
@validate_arguments
def get_project_workflow(project: Union[str, dict]):
    """Gets project's workflow.

    Return value example: [{ "step" : <step_num>, "className" : <annotation_class>, "tool" : <tool_num>, ...},...]

    :param project: project name or metadata
    :type project: str or dict

    :return: project workflow
    :rtype: list of dicts
    """
    project_name, folder_name = extract_project_folder(project)
    workflow = controller.get_project_workflow(project_name=project_name)
    if workflow.errors:
        raise AppException(workflow.errors)
    return workflow.data


@Trackable
@validate_arguments
def search_annotation_classes(
    project: Union[NotEmptyStr, dict], name_prefix: Optional[str] = None
):
    """Searches annotation classes by name_prefix (case-insensitive)

    :param project: project name
    :type project: str
    :param name_prefix: name prefix for search. If None all annotation classes
     will be returned
    :type name_prefix: str

    :return: annotation classes of the project
    :rtype: list of dicts
    """
    project_name, folder_name = extract_project_folder(project)
    classes = controller.search_annotation_classes(project_name, name_prefix)
    classes = [BaseSerializers(attribute).serialize() for attribute in classes.data]
    return classes


@Trackable
@validate_arguments
def set_project_default_image_quality_in_editor(
    project: Union[NotEmptyStr, dict], image_quality_in_editor: Optional[str],
):
    """Sets project's default image quality in editor setting.

    :param project: project name or metadata
    :type project: str or dict
    :param image_quality_in_editor: new setting value, should be "original" or "compressed"
    :type image_quality_in_editor: str
    """
    project_name, folder_name = extract_project_folder(project)
    image_quality_in_editor = ImageQuality.get_value(image_quality_in_editor)

    response = controller.set_project_settings(
        project_name=project_name,
        new_settings=[{"attribute": "ImageQuality", "value": image_quality_in_editor}],
    )
    if response.errors:
        raise AppException(response.errors)
    return response.data


@Trackable
@validate_arguments
def pin_image(
    project: Union[NotEmptyStr, dict], image_name: str, pin: Optional[StrictBool] = True
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
    controller.update_image(
        project_name=project_name,
        image_name=image_name,
        folder_name=folder_name,
        is_pinned=int(pin),
    )


@Trackable
@validate_arguments
def get_image_metadata(
    project: Union[NotEmptyStr, dict], image_name: str, *args, **kwargs
):
    """Returns image metadata

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image_name: str

    :return: metadata of image
    :rtype: dict
    """
    project_name, folder_name = extract_project_folder(project)
    project = controller._get_project(project_name)
    response = controller.get_image_metadata(project_name, folder_name, image_name)

    if response.errors:
        raise AppException(response.errors)
    return ImageSerializer(response.data).serialize_by_project(project)


@Trackable
@validate_arguments
def set_images_annotation_statuses(
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
    project_name, folder_name = extract_project_folder(project)
    response = controller.set_images_annotation_statuses(
        project_name, folder_name, image_names, annotation_status
    )
    if response.errors:
        raise AppException(response.errors)
    logger.info("Annotations status of images changed")


@Trackable
@validate_arguments
def delete_images(
    project: Union[NotEmptyStr, dict], image_names: Optional[List[str]] = None
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

    response = controller.delete_images(
        project_name=project_name, folder_name=folder_name, image_names=image_names
    )
    if response.errors:
        raise AppException(response.errors)

    logger.info(
        f"Images deleted in project {project_name}{'/' + folder_name if folder_name else ''}"
    )


@Trackable
@validate_arguments
def assign_images(project: Union[NotEmptyStr, dict], image_names: List[str], user: str):
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
    project_name, folder_name = extract_project_folder(project)
    project = controller.get_project_metadata(project_name).data

    if project["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(LIMITED_FUNCTIONS[project["project"].project_type])

    if not folder_name:
        folder_name = "root"
    contributors = (
        controller.get_project_metadata(
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

    response = controller.assign_images(project_name, folder_name, image_names, user)
    if not response.errors:
        logger.info(f"Assign images to user {user}")
    else:
        raise AppException(response.errors)


@Trackable
@validate_arguments
def unassign_images(project: Union[NotEmptyStr, dict], image_names: List[NotEmptyStr]):
    """Removes assignment of given images for all assignees.With SDK,
    the user can be assigned to a role in the project with the share_project
    function.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_names: list of image unassign
    :type image_names: list of str
    """
    project_name, folder_name = extract_project_folder(project)

    response = controller.un_assign_images(
        project_name=project_name, folder_name=folder_name, image_names=image_names
    )
    if response.errors:
        raise AppException(response.errors)


@Trackable
@validate_arguments
def unassign_folder(project_name: NotEmptyStr, folder_name: NotEmptyStr):
    """Removes assignment of given folder for all assignees.
    With SDK, the user can be assigned to a role in the project
    with the share_project function.

    :param project_name: project name
    :type project_name: str
    :param folder_name: folder name to remove assignees
    :type folder_name: str
    """
    response = controller.un_assign_folder(
        project_name=project_name, folder_name=folder_name
    )
    if response.errors:
        raise AppException(response.errors)


@Trackable
@validate_arguments
def assign_folder(
    project_name: NotEmptyStr, folder_name: NotEmptyStr, users: List[NotEmptyStr]
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
        controller.get_project_metadata(
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

    response = controller.assign_folder(
        project_name=project_name, folder_name=folder_name, users=list(verified_users)
    )

    if response.errors:
        raise AppException(response.errors)


@Trackable
@validate_arguments
def share_project(
    project_name: NotEmptyStr, user: Union[str, dict], user_role: NotEmptyStr
):
    """Share project with user.

    :param project_name: project name
    :type project_name: str
    :param user: user email or metadata of the user to share project with
    :type user: str or dict
    :param user_role: user role to apply, one of Admin , Annotator , QA , Customer , Viewer
    :type user_role: str
    """
    if isinstance(user, dict):
        user_id = user["id"]
    else:
        response = controller.search_team_contributors(email=user)
        if not response.data:
            raise AppException(f"User {user} not found.")
        user_id = response.data[0]["id"]
    response = controller.share_project(
        project_name=project_name, user_id=user_id, user_role=user_role
    )
    if response.errors:
        raise AppException(response.errors)


@Trackable
@validate_arguments
def get_image_annotations(project: Union[NotEmptyStr, dict], image_name: NotEmptyStr):
    """Get annotations of the image.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image_name: str

    :return: dict object with following keys:
        "annotation_json": dict object of the annotation,
        "annotation_json_filename": filename on server,
        "annotation_mask": mask (for pixel),
        "annotation_mask_filename": mask filename on server
    :rtype: dict
    """
    project_name, folder_name = extract_project_folder(project)
    res = controller.get_image_annotations(
        project_name=project_name, folder_name=folder_name, image_name=image_name
    )
    if res.errors:
        raise AppException(res.errors)
    return res.data


@validate_arguments
def upload_images_from_folder_to_project(
    project: Union[NotEmptyStr, dict],
    folder_path: Union[NotEmptyStr, Path],
    extensions: Optional[
        Union[List[NotEmptyStr], Tuple[NotEmptyStr]]
    ] = constances.DEFAULT_IMAGE_EXTENSIONS,
    annotation_status="NotStarted",
    from_s3_bucket=None,
    exclude_file_patterns: Optional[
        Iterable[NotEmptyStr]
    ] = constances.DEFAULT_FILE_EXCLUDE_PATTERNS,
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
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
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
            constances.DEFAULT_FILE_EXCLUDE_PATTERNS
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

    use_case = controller.upload_images_from_folder_to_project(
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
            "%s already existing images found that won't be uploaded.", len(duplicates)
        )
    logger.info(
        "Uploading %s images to project %s.", len(images_to_upload), project_folder_name
    )
    if not images_to_upload:
        return [], [], duplicates
    if use_case.is_valid():
        with tqdm(total=len(images_to_upload), desc="Uploading images") as progress_bar:
            for _ in use_case.execute():
                progress_bar.update(1)
        return use_case.data
    raise AppException(use_case.response.errors)


@Trackable
@validate_arguments
def get_project_image_count(
    project: Union[NotEmptyStr, dict], with_all_subfolders: Optional[StrictBool] = False
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

    response = controller.get_project_image_count(
        project_name=project_name,
        folder_name=folder_name,
        with_all_subfolders=with_all_subfolders,
    )
    if response.errors:
        raise AppException(response.errors)
    return response.data


@Trackable
@validate_arguments
def download_image_annotations(
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
    res = controller.download_image_annotations(
        project_name=project_name,
        folder_name=folder_name,
        image_name=image_name,
        destination=local_dir_path,
    )
    if res.errors:
        raise AppException(res.errors)
    return res.data


@Trackable
@validate_arguments
def get_exports(project: NotEmptyStr, return_metadata: Optional[StrictBool] = False):
    """Get all prepared exports of the project.

    :param project: project name
    :type project: str
    :param return_metadata: return metadata of images instead of names
    :type return_metadata: bool

    :return: names or metadata objects of the all prepared exports of the project
    :rtype: list of strs or dicts
    """
    response = controller.get_exports(
        project_name=project, return_metadata=return_metadata
    )
    return response.data


@Trackable
@validate_arguments
def prepare_export(
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
    :param annotation_statuses: images with which status to include, if None, ["NotStarted", "InProgress", "QualityCheck", "Returned", "Completed", "Skipped"]  will be chose
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
            constances.AnnotationStatus.NOT_STARTED.name,
            constances.AnnotationStatus.IN_PROGRESS.name,
            constances.AnnotationStatus.QUALITY_CHECK.name,
            constances.AnnotationStatus.RETURNED.name,
            constances.AnnotationStatus.COMPLETED.name,
            constances.AnnotationStatus.SKIPPED.name,
        ]
    response = controller.prepare_export(
        project_name=project_name,
        folder_names=folders,
        include_fuse=include_fuse,
        only_pinned=only_pinned,
        annotation_statuses=annotation_statuses,
    )
    if response.errors:
        raise AppException(response.errors)
    return response.data


@Trackable
@validate_arguments
def upload_videos_from_folder_to_project(
    project: Union[NotEmptyStr, dict],
    folder_path: Union[NotEmptyStr, Path],
    extensions: Optional[
        Union[Tuple[NotEmptyStr], List[NotEmptyStr]]
    ] = constances.DEFAULT_VIDEO_EXTENSIONS,
    exclude_file_patterns: Optional[List[NotEmptyStr]] = [],
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
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded and not-uploaded video frame images' filenames
    :rtype: tuple of list of strs
    """

    project_name, folder_name = extract_project_folder(project)
    project = controller.get_project_metadata(project_name).data
    if project["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(LIMITED_FUNCTIONS[project["project"].project_type])

    video_paths = []
    for extension in extensions:
        if not recursive_subfolders:
            video_paths += list(Path(folder_path).glob(f"*.{extension.lower()}"))
            if os.name != "nt":
                video_paths += list(Path(folder_path).glob(f"*.{extension.upper()}"))
        else:
            logger.warning(
                "When using recursive subfolder parsing same name videos in different subfolders will overwrite each other."
            )
            video_paths += list(Path(folder_path).rglob(f"*.{extension.lower()}"))
            if os.name != "nt":
                video_paths += list(Path(folder_path).rglob(f"*.{extension.upper()}"))
    filtered_paths = []
    video_paths = [str(path) for path in video_paths]
    for path in video_paths:

        not_in_exclude_list = [x not in Path(path).name for x in exclude_file_patterns]
        if all(not_in_exclude_list):
            filtered_paths.append(path)

    project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")
    logger.info(
        f"Uploading all videos with extensions {extensions} from {str(folder_path)} to project {project_name}. Excluded file patterns are: {exclude_file_patterns}."
    )
    uploaded_paths = []
    for path in filtered_paths:
        progress_bar = None
        with tempfile.TemporaryDirectory() as temp_path:
            frame_names = VideoPlugin.get_extractable_frames(
                path, start_time, end_time, target_fps
            )
            duplicate_images = (
                controller.get_duplicate_images(
                    project_name=project_name,
                    folder_name=folder_name,
                    images=frame_names,
                )
                .execute()
                .data
            )
            duplicate_images = [image.name for image in duplicate_images]
            frames_generator = controller.extract_video_frames(
                project_name=project_name,
                folder_name=folder_name,
                video_path=path,
                extract_path=temp_path,
                target_fps=target_fps,
                start_time=start_time,
                end_time=end_time,
                annotation_status=annotation_status,
                image_quality_in_editor=image_quality_in_editor,
            )
            total_frames_count = len(frame_names)
            logger.info(f"Video frame count is {total_frames_count}.")
            logger.info(
                f"Extracted {total_frames_count} frames from video. Now uploading to platform.",
            )
            logger.info(
                f"Uploading {total_frames_count} images to project {str(project_folder_name)}."
            )
            if len(duplicate_images):
                logger.warning(
                    f"{len(duplicate_images)} already existing images found that won't be uploaded."
                )
            if set(duplicate_images) == set(frame_names):
                continue

            for _ in frames_generator:
                use_case = controller.upload_images_from_folder_to_project(
                    project_name=project_name,
                    folder_name=folder_name,
                    folder_path=temp_path,
                    annotation_status=annotation_status,
                    image_quality_in_editor=image_quality_in_editor,
                )

                images_to_upload, duplicates = use_case.images_to_upload
                if not len(images_to_upload):
                    continue
                if not progress_bar:
                    progress_bar = tqdm(
                        total=total_frames_count, desc="Uploading images"
                    )
                if use_case.is_valid():
                    for _ in use_case.execute():
                        progress_bar.update()
                    uploaded, failed_images, _ = use_case.response.data
                    uploaded_paths.extend(uploaded)
                    if failed_images:
                        logger.warning(f"Failed {len(failed_images)}.")
                    files = os.listdir(temp_path)
                    image_paths = [f"{temp_path}/{f}" for f in files]
                    for path in image_paths:
                        os.remove(path)
                else:
                    raise AppException(use_case.response.errors)

    return uploaded_paths


@Trackable
@validate_arguments
def upload_video_to_project(
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

    project = controller.get_project_metadata(project_name).data
    if project["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(LIMITED_FUNCTIONS[project["project"].project_type])
    project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")

    uploaded_paths = []
    path = video_path
    progress_bar = None
    with tempfile.TemporaryDirectory() as temp_path:
        frame_names = VideoPlugin.get_extractable_frames(
            video_path, start_time, end_time, target_fps
        )
        duplicate_images = (
            controller.get_duplicate_images(
                project_name=project_name, folder_name=folder_name, images=frame_names,
            )
            .execute()
            .data
        )
        duplicate_images = [image.name for image in duplicate_images]
        frames_generator = controller.extract_video_frames(
            project_name=project_name,
            folder_name=folder_name,
            video_path=path,
            extract_path=temp_path,
            target_fps=target_fps,
            start_time=start_time,
            end_time=end_time,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        )
        total_frames_count = len(frame_names)
        logger.info(
            f"Extracted {total_frames_count} frames from video. Now uploading to platform.",
        )
        logger.info(
            f"Uploading {total_frames_count} images to project {str(project_folder_name)}."
        )
        if len(duplicate_images):
            logger.warning(
                f"{len(duplicate_images)} already existing images found that won't be uploaded."
            )
        if set(duplicate_images) == set(frame_names):
            return []

        for _ in frames_generator:
            use_case = controller.upload_images_from_folder_to_project(
                project_name=project_name,
                folder_name=folder_name,
                folder_path=temp_path,
                annotation_status=annotation_status,
                image_quality_in_editor=image_quality_in_editor,
            )

            images_to_upload, duplicates = use_case.images_to_upload
            if not len(images_to_upload):
                continue
            if not progress_bar:
                progress_bar = tqdm(total=total_frames_count, desc="Uploading images")
            if use_case.is_valid():
                for _ in use_case.execute():
                    progress_bar.update()
                uploaded, failed_images, _ = use_case.response.data
                uploaded_paths.extend(uploaded)
                if failed_images:
                    logger.warning(f"Failed {len(failed_images)}.")
                files = os.listdir(temp_path)
                image_paths = [f"{temp_path}/{f}" for f in files]
                for path in image_paths:
                    os.remove(path)
            else:
                raise AppException(use_case.response.errors)

    return uploaded_paths


@Trackable
@validate_arguments
def create_annotation_class(
    project: Union[Project, NotEmptyStr],
    name: NotEmptyStr,
    color: NotEmptyStr,
    attribute_groups: Optional[List[AttributeGroup]] = None,
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

    :return: new class metadata
    :rtype: dict
    """
    if isinstance(project, Project):
        project = project.dict()
    attribute_groups = (
        list(map(lambda x: x.dict(), attribute_groups)) if attribute_groups else None
    )
    response = controller.create_annotation_class(
        project_name=project, name=name, color=color, attribute_groups=attribute_groups
    )
    return response.data.to_dict()


@Trackable
@validate_arguments
def delete_annotation_class(
    project: NotEmptyStr, annotation_class: Union[dict, NotEmptyStr]
):
    """Deletes annotation class from project

    :param project: project name
    :type project: str
    :param annotation_class: annotation class name or  metadata
    :type annotation_class: str or dict
    """
    controller.delete_annotation_class(
        project_name=project, annotation_class_name=annotation_class
    )


@Trackable
@validate_arguments
def download_annotation_classes_json(project: NotEmptyStr, folder: Union[str, Path]):
    """Downloads project classes.json to folder

    :param project: project name
    :type project: str
    :param folder: folder to download to
    :type folder: Path-like (str or Path)

    :return: path of the download file
    :rtype: str
    """
    response = controller.download_annotation_classes(
        project_name=project, download_path=folder
    )
    if response.errors:
        raise AppException(response.errors)
    return response.data


@Trackable
@validate_arguments
def create_annotation_classes_from_classes_json(
    project: Union[NotEmptyStr, dict],
    classes_json: Union[List[ClassesJson], str, Path],
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
    if not isinstance(classes_json, list):
        logger.info(
            "Creating annotation classes in project %s from %s.", project, classes_json,
        )
        if from_s3_bucket:
            from_session = boto3.Session()
            from_s3 = from_session.resource("s3")
            file = io.BytesIO()
            from_s3_object = from_s3.Object(from_s3_bucket, classes_json)
            from_s3_object.download_fileobj(file)
            file.seek(0)
            annotation_classes = parse_obj_as(List[ClassesJson], json.load(file))
        else:
            annotation_classes = parse_obj_as(
                List[ClassesJson], json.load(open(classes_json))
            )

    else:
        annotation_classes = classes_json

    annotation_classes = list(
        map(lambda annotation_class: annotation_class.dict(), annotation_classes)
    )
    response = controller.create_annotation_classes(
        project_name=project, annotation_classes=annotation_classes,
    )
    return response.data


@Trackable
@validate_arguments
def download_export(
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

    use_case = controller.download_export(
        project_name=project_name,
        export_name=export_name,
        folder_path=folder_path,
        extract_zip_contents=extract_zip_contents,
        to_s3_bucket=to_s3_bucket,
    )
    if use_case.is_valid():
        if to_s3_bucket:
            with tqdm(
                total=use_case.get_upload_files_count(), desc="Uploading"
            ) as progress_bar:
                for _ in use_case.execute():
                    progress_bar.update()
            progress_bar.close()
        else:
            for _ in use_case.execute():
                continue
        logger.info(use_case.response.data)
    else:
        raise AppException(use_case.response.errors)


@Trackable
@validate_arguments
def set_image_annotation_status(
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
    project_name, folder_name = extract_project_folder(project)
    project_entity = controller._get_project(project_name)
    response = controller.set_images_annotation_statuses(
        project_name, folder_name, [image_name], annotation_status
    )
    if response.errors:
        raise AppException(response.errors)
    image = controller.get_image_metadata(project_name, folder_name, image_name).data
    return ImageSerializer(image).serialize_by_project(project=project_entity)


@Trackable
@validate_arguments
def set_project_workflow(project: Union[NotEmptyStr, dict], new_workflow: List[dict]):
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
    response = controller.set_project_workflow(
        project_name=project_name, steps=new_workflow
    )
    if response.errors:
        raise AppException(response.errors)


@Trackable
@validate_arguments
def download_image(
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
    response = controller.download_image(
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


@Trackable
@validate_arguments
def attach_image_urls_to_project(
    project: Union[NotEmptyStr, dict],
    attachments: Union[str, Path],
    annotation_status: Optional[AnnotationStatuses] = "NotStarted",
):
    """Link images on external storage to SuperAnnotate.

    :param project: project name or project folder path
    :type project: str or dict
    :param attachments: path to csv file on attachments metadata
    :type attachments: Path-like (str or Path)
    :param annotation_status: value to set the annotation statuses of the linked images: NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :return: list of linked image names, list of failed image names, list of duplicate image names
    :rtype: tuple
    """
    project_name, folder_name = extract_project_folder(project)
    project = controller.get_project_metadata(project_name).data
    project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")

    if project["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(
            constances.INVALID_PROJECT_TYPE_TO_PROCESS.format(
                constances.ProjectType.get_name(project["project"].project_type)
            )
        )
    images_to_upload, duplicate_images = get_paths_and_duplicated_from_csv(attachments)
    use_case = controller.interactive_attach_urls(
        project_name=project_name,
        folder_name=folder_name,
        files=ImageSerializer.deserialize(images_to_upload),  # noqa: E203
        annotation_status=annotation_status,
    )
    if len(duplicate_images):
        logger.warning(
            constances.ALREADY_EXISTING_FILES_WARNING.format(len(duplicate_images))
        )

    if use_case.is_valid():
        logger.info(
            constances.ATTACHING_FILES_MESSAGE.format(
                len(images_to_upload), project_folder_name
            )
        )
        with tqdm(
            total=use_case.attachments_count, desc="Attaching urls"
        ) as progress_bar:
            for attached in use_case.execute():
                progress_bar.update(attached)
        uploaded, duplications = use_case.data
        uploaded = [i["name"] for i in uploaded]
        duplications.extend(duplicate_images)
        failed_images = [
            image["name"]
            for image in images_to_upload
            if image["name"] not in uploaded + duplications
        ]
        return uploaded, failed_images, duplications
    raise AppException(use_case.response.errors)


@Trackable
@validate_arguments
def attach_video_urls_to_project(
    project: Union[NotEmptyStr, dict],
    attachments: Union[str, Path],
    annotation_status: Optional[AnnotationStatuses] = "NotStarted",
):
    """Link videos on external storage to SuperAnnotate.

    :param project: project name or project folder path
    :type project: str or dict
    :param attachments: path to csv file on attachments metadata
    :type attachments: Path-like (str or Path)
    :param annotation_status: value to set the annotation statuses of the linked videos: NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :return: attached videos, failed videos, skipped videos
    :rtype: (list, list, list)
    """
    project_name, folder_name = extract_project_folder(project)
    project = controller.get_project_metadata(project_name).data
    project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")

    if project["project"].project_type != constances.ProjectType.VIDEO.value:
        raise AppException(
            constances.INVALID_PROJECT_TYPE_TO_PROCESS.format(
                constances.ProjectType.get_name(project["project"].project_type)
            )
        )

    images_to_upload, duplicate_images = get_paths_and_duplicated_from_csv(attachments)
    use_case = controller.interactive_attach_urls(
        project_name=project_name,
        folder_name=folder_name,
        files=ImageSerializer.deserialize(images_to_upload),  # noqa: E203
        annotation_status=annotation_status,
    )
    if len(duplicate_images):
        logger.warning(
            constances.ALREADY_EXISTING_FILES_WARNING.format(len(duplicate_images))
        )

    if use_case.is_valid():
        logger.info(
            constances.ATTACHING_FILES_MESSAGE.format(
                len(images_to_upload), project_folder_name
            )
        )
        with tqdm(
            total=use_case.attachments_count, desc="Attaching urls"
        ) as progress_bar:
            for attached in use_case.execute():
                progress_bar.update(attached)
        uploaded, duplications = use_case.data
        uploaded = [i["name"] for i in uploaded]
        duplications.extend(duplicate_images)
        failed_images = [
            image["name"]
            for image in images_to_upload
            if image["name"] not in uploaded + duplications
        ]
        return uploaded, failed_images, duplications
    raise AppException(use_case.response.errors)


@Trackable
@validate_arguments
def upload_annotations_from_folder_to_project(
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
    response = controller.upload_annotations_from_folder(
        project_name=project_name,
        folder_name=folder_name,
        annotation_paths=annotation_paths,  # noqa: E203
        client_s3_bucket=from_s3_bucket,
        folder_path=folder_path,
    )
    if response.errors:
        raise AppException(response.errors)
    return response.data


@Trackable
@validate_arguments
def upload_preannotations_from_folder_to_project(
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
    project = controller.get_project_metadata(project_name).data
    if project["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(LIMITED_FUNCTIONS[project["project"].project_type])
    if recursive_subfolders:
        logger.info(
            "When using recursive subfolder parsing same name annotations in different "
            "subfolders will overwrite each other.",
        )
    logger.info(
        "The JSON files should follow a specific naming convention, matching file names already present "
        "on the platform. Existing annotations will be overwritten"
    )
    logger.info("Existing annotations will be overwritten.",)
    annotation_paths = get_annotation_paths(
        folder_path, from_s3_bucket, recursive_subfolders
    )
    logger.info(
        f"Uploading {len(annotation_paths)} annotations from {folder_path} to the project {project_folder_name}."
    )
    response = controller.upload_annotations_from_folder(
        project_name=project_name,
        folder_name=folder_name,
        annotation_paths=annotation_paths,  # noqa: E203
        client_s3_bucket=from_s3_bucket,
        is_pre_annotations=True,
    )
    if response.errors:
        raise AppException(response.errors)
    return response.data


@Trackable
@validate_arguments
def upload_image_annotations(
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

    project = controller.get_project_metadata(project_name).data
    if project["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(LIMITED_FUNCTIONS[project["project"].project_type])

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
    response = controller.upload_image_annotations(
        project_name=project_name,
        folder_name=folder_name,
        image_name=image_name,
        annotations=annotation_json,
        mask=mask,
        verbose=verbose,
    )
    if response.errors:
        raise AppException(response.errors)


@Trackable
@validate_arguments
def download_model(model: MLModel, output_dir: Union[str, Path]):
    """Downloads the neural network and related files
    which are the <model_name>.pth/pkl. <model_name>.json, <model_name>.yaml, classes_mapper.json

    :param model: the model that needs to be downloaded
    :type  model: dict
    :param output_dir: the directiory in which the files will be saved
    :type output_dir: str
    :return: the metadata of the model
    :rtype: dict
    """
    res = controller.download_ml_model(
        model_data=model.dict(), download_path=output_dir
    )
    if res.errors:
        logger.error("\n".join([str(error) for error in res.errors]))
    else:
        return BaseSerializers(res.data).serialize()


@Trackable
@validate_arguments
def benchmark(
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

    project = controller.get_project_metadata(project_name).data
    if project["project"].project_type in [
        constances.ProjectType.VIDEO.value,
        constances.ProjectType.DOCUMENT.value,
    ]:
        raise AppException(LIMITED_FUNCTIONS[project["project"].project_type])

    if not export_root:
        with tempfile.TemporaryDirectory() as temp_dir:
            response = controller.benchmark(
                project_name=project_name,
                ground_truth_folder_name=gt_folder,
                folder_names=folder_names,
                export_root=temp_dir,
                image_list=image_list,
                annot_type=annot_type,
                show_plots=show_plots,
            )

    else:
        response = controller.benchmark(
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


@Trackable
@validate_arguments
def consensus(
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
            response = controller.consensus(
                project_name=project,
                folder_names=folder_names,
                export_path=export_root,
                image_list=image_list,
                annot_type=annot_type,
                show_plots=show_plots,
            )

    else:
        response = controller.consensus(
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


@Trackable
@validate_arguments
def run_prediction(
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

    response = controller.run_prediction(
        project_name=project_name,
        images_list=images_list,
        model_name=model_name,
        folder_name=folder_name,
    )
    if response.errors:
        raise AppException(response.errors)
    return response.data


@Trackable
@validate_arguments
def add_annotation_bbox_to_image(
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
    response = controller.get_image_annotations(
        project_name=project_name, folder_name=folder_name, image_name=image_name
    )
    annotations = response.data["annotation_json"]
    annotations = add_annotation_bbox_to_json(
        annotations,
        bbox,
        annotation_class_name,
        annotation_class_attributes,
        error,
        image_name,
    )

    controller.upload_image_annotations(
        *extract_project_folder(project), image_name, annotations
    )


@Trackable
@validate_arguments
def add_annotation_point_to_image(
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
    response = controller.get_image_annotations(
        project_name=project_name, folder_name=folder_name, image_name=image_name
    )
    annotations = response.data["annotation_json"]
    annotations = add_annotation_point_to_json(
        annotations,
        point,
        annotation_class_name,
        image_name,
        annotation_class_attributes,
        error,
    )
    controller.upload_image_annotations(
        *extract_project_folder(project), image_name, annotations
    )


@Trackable
@validate_arguments
def add_annotation_comment_to_image(
    project: NotEmptyStr,
    image_name: NotEmptyStr,
    comment_text: NotEmptyStr,
    comment_coords: List[float],
    comment_author: NotEmptyStr,
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
    response = controller.get_image_annotations(
        project_name=project_name, folder_name=folder_name, image_name=image_name
    )
    annotations = response.data["annotation_json"]
    annotations = add_annotation_comment_to_json(
        annotations,
        comment_text,
        comment_coords,
        comment_author,
        resolved=resolved,
        image_name=image_name,
    )
    controller.upload_image_annotations(
        *extract_project_folder(project), image_name, annotations
    )


@Trackable
@validate_arguments
def search_images_all_folders(
    project: NotEmptyStr,
    image_name_prefix: Optional[NotEmptyStr] = None,
    annotation_status: Optional[NotEmptyStr] = None,
    return_metadata: Optional[StrictBool] = False,
):
    """Search images by name_prefix (case-insensitive) and annotation status in
    project and all of its folders

    :param project: project name
    :type project: str
    :param image_name_prefix: image name prefix for search
    :type image_name_prefix: str
    :param annotation_status: if not None, annotation statuses of images to filter,
                              should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :param return_metadata: return metadata of images instead of names
    :type return_metadata: bool

    :return: metadata of found images or image names
    :rtype: list of dicts or strs
    """

    project_entity = controller._get_project(project)
    res = controller.list_images(
        project_name=project,
        name_prefix=image_name_prefix,
        annotation_status=annotation_status,
    )
    if return_metadata:
        return [
            ImageSerializer(image).serialize_by_project(project=project_entity)
            for image in res.data
        ]
    return [image.name for image in res.data]


@Trackable
@validate_arguments
def upload_image_to_project(
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

    response = controller.upload_image_to_project(
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
    res = controller.search_models(
        name=name,
        model_type=type_,
        project_id=project_id,
        task=task,
        include_global=include_global,
    )
    return res.data


@Trackable
@validate_arguments
def upload_images_to_project(
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

    use_case = controller.upload_images_to_project(
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
            "%s already existing images found that won't be uploaded.", len(duplicates)
        )
    logger.info(f"Uploading {len(images_to_upload)} images to project {project}.")
    uploaded, failed_images, duplications = [], [], duplicates
    if not images_to_upload:
        return uploaded, failed_images, duplications
    if use_case.is_valid():
        with tqdm(total=len(images_to_upload), desc="Uploading images") as progress_bar:
            for _ in use_case.execute():
                progress_bar.update(1)
        uploaded, failed_images, duplications = use_case.data
        if duplications:
            logger.info(f"Duplicated images {', '.join(duplications)}")
        return uploaded, failed_images, duplications
    raise AppException(use_case.response.errors)


@Trackable
@validate_arguments
def aggregate_annotations_as_df(
    project_root: Union[NotEmptyStr, Path],
    project_type: ProjectTypes,
    folder_names: Optional[List[Union[Path, NotEmptyStr]]] = None,
):
    """Aggregate annotations as pandas dataframe from project root.

    :param project_root: the export path of the project
    :type project_root: Pathlike (str or Path)

    :param project_type: the project type, Vector/Pixel or Video
    :type project_type: str

    :param folder_names: Aggregate the specified folders from project_root.
     If None aggregate all folders in the project_root
    :type folder_names: list of Pathlike (str or Path) objects

    :return: DataFrame on annotations
    :rtype: pandas DataFrame
    """
    if project_type in (
        constances.ProjectType.VECTOR.name,
        constances.ProjectType.PIXEL.name,
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
    elif project_type == constances.ProjectType.VIDEO.name:
        from superannotate.lib.app.analytics.aggregators import DataAggregator

        return DataAggregator(
            project_type=project_type,
            project_root=project_root,
            folder_names=folder_names,
        ).aggregate_annotations_as_df()
    else:
        raise AppException(constances.DEPRECATED_DOCUMENT_PROJECTS_MESSAGE)


@Trackable
@validate_arguments
def delete_annotations(
    project: NotEmptyStr, image_names: Optional[List[NotEmptyStr]] = None
):
    """
    Delete image annotations from a given list of images.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_names:  image names. If None, all image annotations from a given project/folder will be deleted.
    :type image_names: list of strs
    """

    project_name, folder_name = extract_project_folder(project)

    response = controller.delete_annotations(
        project_name=project_name, folder_name=folder_name, image_names=image_names
    )
    if response.errors:
        raise AppException(response.errors)


@Trackable
@validate_arguments
def attach_document_urls_to_project(
    project: Union[NotEmptyStr, dict],
    attachments: Union[Path, NotEmptyStr],
    annotation_status: Optional[AnnotationStatuses] = "NotStarted",
):
    """Link documents on external storage to SuperAnnotate.

    :param project: project name or project folder path
    :type project: str or dict
    :param attachments: path to csv file on attachments metadata
    :type attachments: Path-like (str or Path)
    :param annotation_status: value to set the annotation statuses of the linked documents: NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :return: list of attached documents, list of not attached documents, list of skipped documents
    :rtype: tuple
    """
    project_name, folder_name = extract_project_folder(project)
    project = controller.get_project_metadata(project_name).data
    project_folder_name = project_name + (f"/{folder_name}" if folder_name else "")

    if project["project"].project_type != constances.ProjectType.DOCUMENT.value:
        raise AppException(
            constances.INVALID_PROJECT_TYPE_TO_PROCESS.format(
                constances.ProjectType.get_name(project["project"].project_type)
            )
        )

    images_to_upload, duplicate_images = get_paths_and_duplicated_from_csv(attachments)

    use_case = controller.interactive_attach_urls(
        project_name=project_name,
        folder_name=folder_name,
        files=ImageSerializer.deserialize(images_to_upload),  # noqa: E203
        annotation_status=annotation_status,
    )
    if len(duplicate_images):
        logger.warning(
            constances.ALREADY_EXISTING_FILES_WARNING.format(len(duplicate_images))
        )
    if use_case.is_valid():
        logger.info(
            constances.ATTACHING_FILES_MESSAGE.format(
                len(images_to_upload), project_folder_name
            )
        )
        with tqdm(
            total=use_case.attachments_count, desc="Attaching urls"
        ) as progress_bar:
            for attached in use_case.execute():
                progress_bar.update(attached)
        uploaded, duplications = use_case.data
        uploaded = [i["name"] for i in uploaded]
        duplications.extend(duplicate_images)
        failed_images = [
            image["name"]
            for image in images_to_upload
            if image["name"] not in uploaded + duplications
        ]
        return uploaded, failed_images, duplications
    raise AppException(use_case.response.errors)


@Trackable
@validate_arguments
def validate_annotations(
    project_type: ProjectTypes, annotations_json: Union[NotEmptyStr, Path]
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
        response = controller.validate_annotations(
            project_type, annotation_data, allow_extra=False
        )
        if response.errors:
            raise AppException(response.errors)
        is_valid, _ = response.data
        if is_valid:
            return True
        print(response.report)
        return False


@Trackable
@validate_arguments
def add_contributors_to_project(
    project: NotEmptyStr, emails: conlist(EmailStr, min_items=1), role: AnnotatorRole
) -> Tuple[List[str], List[str]]:
    """Add contributors to project.

    :param project: project name
    :type project: str

    :param emails: users email
    :type emails: list

    :param role: user role to apply, one of Admin , Annotator , QA
    :type role: str

    return: lists of added,  skipped contributors of the project
    rtype: tuple (2 members) of lists of strs
    """
    response = controller.add_contributors_to_project(
        project_name=project, emails=emails, role=role
    )
    if response.errors:
        raise AppException(response.errors)
    return response.data


@Trackable
@validate_arguments
def invite_contributors_to_team(emails: conlist(EmailStr, min_items=1), admin: StrictBool = False) -> Tuple[List[str], List[str]]:
    """Invites contributors to the team.

    :param emails: list of contributor emails
    :type emails: list

    :param admin: enables admin privileges for the contributor
    :type admin: bool

    return: lists of invited, skipped contributors of the team
    rtype: tuple (2 members) of lists of strs
    """
    response = controller.invite_contributors_to_team(emails=emails, set_admin=admin)
    if response.errors:
        raise AppException(response.errors)
    return response.data
