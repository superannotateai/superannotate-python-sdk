import concurrent.futures
import json
import logging
import os
import tempfile
from collections import Counter
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import boto3
import lib.core as constances
from lib.app.exceptions import AppException
from lib.app.exceptions import EmptyOutputError
from lib.app.helpers import split_project_path
from lib.app.serializers import BaseSerializers
from lib.app.serializers import ImageSerializer
from lib.app.serializers import ProjectSerializer
from lib.app.serializers import TeamSerializer
from lib.core.exceptions import AppValidationException
from lib.core.response import Response
from lib.infrastructure.controller import Controller
from lib.infrastructure.repositories import ConfigRepository
from lib.infrastructure.services import SuperannotateBackendService

logger = logging.getLogger()


controller = Controller(
    backend_client=SuperannotateBackendService(
        api_url=constances.BACKEND_URL,
        auth_token=ConfigRepository().get_one("token"),
        logger=logger,
    ),
    response=Response(),
)


def get_team_metadata():

    """Returns team metadata

    :return: team metadata
    :rtype: dict
    """
    response = controller.get_team()
    return TeamSerializer(response.data).serialize()


def invite_contributor_to_team(email, admin=False):
    """Invites a contributor to team

    :param email: email of the contributor
    :type email: str
    :param admin: enables admin priviledges for the contributor
    :type admin: bool
    """
    controller.invite_contributor(email, is_admin=admin)


def delete_contributor_to_team_invitation(email):
    """Deletes team contributor invitation

    :param email: invitation email
    :type email: str
    """
    controller.delete_contributor_invitation(email)


def search_team_contributors(
    email=None, first_name=None, last_name=None, return_metadata=True
):
    """Search for contributors in the team

    :param email: filter by email
    :type email: str
    :param first_name: filter by first name
    :type first_name: str
    :param last_name: filter by last name
    :type last_name: str

    :return: metadata of found users
    :rtype: list of dicts
    """

    contributors = controller.search_team_contributors(
        email=email, first_name=first_name, last_name=last_name
    )
    if not return_metadata:
        return [contributor["email"] for contributor in contributors]
    return contributors


def search_projects(
    name=None, return_metadata=False, include_complete_image_count=False
):
    """Project name based case-insensitive search for projects.
    If **name** is None, all the projects will be returned.

    :param name: search string
    :type name: str
    :param return_metadata: return metadata of projects instead of names
    :type return_metadata: bool

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


def create_project(project_name, project_description, project_type):
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
    projects = controller.search_project(name=project_name).data
    if projects:
        raise AppException(
            f"Project with name {project_name} already exists."
            f" Please use unique names for projects to use with SDK."
        )

    result = controller.create_project(
        name=project_name, description=project_description, project_type=project_type
    ).data
    return ProjectSerializer(result).serialize()


def create_project_from_metadata(project_metadata):
    """Create a new project in the team using project metadata object dict.
    Mandatory keys in project_metadata are "name", "description" and "type" (Vector or Pixel)
    Non-mandatory keys: "workflow", "contributors", "settings" and "annotation_classes".

    :return: dict object metadata the new project
    :rtype: dict
    """
    project = controller.create_project(
        name=project_metadata["name"],
        description=project_metadata["description"],
        project_type=project_metadata["type"],
        contributors=project_metadata["contributors"],
        settings=project_metadata["settings"],
        annotation_classes=project_metadata["annotation_classes"],
        workflows=project_metadata["workflow"],
    ).data

    return project


def clone_project(
    project_name,
    from_project,
    project_description=None,
    copy_annotation_classes=True,
    copy_settings=True,
    copy_workflow=True,
    copy_contributors=False,
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
    result = controller.clone_project(
        name=project_name,
        from_name=from_project,
        project_description=project_description,
        copy_annotation_classes=copy_annotation_classes,
        copy_settings=copy_settings,
        copy_workflow=copy_workflow,
        copy_contributors=copy_contributors,
    ).data
    return result


def search_images(
    project, image_name_prefix=None, annotation_status=None, return_metadata=False
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

    project_name, folder_name = split_project_path(project)

    result = controller.search_images(
        project_name=project_name,
        folder_path=folder_name,
        annotation_status=annotation_status,
        image_name_prefix=image_name_prefix,
    ).data
    if return_metadata:
        return [ImageSerializer(image).serialize() for image in result]
    return [image.name for image in result]


def create_folder(project, folder_name):
    """Create a new folder in the project.

    :param project: project name
    :type project: str
    :param folder_name: the new folder's name
    :type folder_name: str

    :return: dict object metadata the new folder
    :rtype: dict
    """

    result = controller.create_folder(project=project, folder_name=folder_name).data
    if result.name != folder_name:
        logger.warning(
            f"Created folder has name {result.name}, since folder with name {folder_name} already existed.",
        )
    logger.info(f"Folder {result.name} created in project {project}")
    return result.to_dict()


def delete_project(project):
    """Deletes the project

        :param project: project name or folder path (e.g., "project1/folder1")
        :type project: str
    """
    name = project
    if isinstance(project, dict):
        name = project["name"]
    controller.delete_project(name=name)


def rename_project(project, new_name):
    """Renames the project

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param new_name: project's new name
    :type new_name: str
    """
    controller.update_project(name=project, project_data={"name": new_name})


def get_folder_metadata(project, folder_name):
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
        raise EmptyOutputError("Couldn't get folder metadata.")
    return result.to_dict()


def delete_folders(project, folder_names):
    """Delete folder in project.

    :param project: project name
    :type project: str
    :param folder_names: to be deleted folders' names
    :type folder_names: list of strs
    """

    controller.delete_folders(project_name=project, folder_names=folder_names)
    logger.info(f"Folders {folder_names} deleted in project {project}")


def get_project_and_folder_metadata(project):
    """Returns project and folder metadata tuple. If folder part is empty,
    than returned folder part is set to None.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param folder_name: folder's name
    :type folder_name: str

    :return: metadata of folder
    :rtype: dict
    """
    project_name, folder_name = split_project_path(project)
    project = ProjectSerializer(
        controller.search_project(project_name).data[0]
    ).serialize()
    folder = None
    if folder_name:
        folder = get_folder_metadata(project_name, folder_name)
    return project, folder


def rename_folder(project, new_folder_name):
    """Renames folder in project.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param new_folder_name: folder's new name
    :type new_folder_name: str
    """
    project_name, folder_name = split_project_path(project)
    controller.update_folder(project_name, folder_name, {"name": new_folder_name})
    logger.info(
        f"Folder {folder_name} renamed to {new_folder_name} in project {project_name}"
    )


def search_folders(project, folder_name=None, return_metadata=False):
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

    if not folder_name:
        data = controller.get_project_folders(project).data
    else:
        data = controller.search_folder(project_name=project, name=folder_name).data
    if return_metadata:
        return data.to_dict()
    return [folder.name for folder in data]


def get_image_bytes(project, image_name, variant="original"):
    """Returns an io.BytesIO() object of the image. Suitable for creating
    PIL.Image out of it.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param variant: which resolution to get, can be 'original' or 'lores'
     (low resolution)
    :type variant: str

    :return: io.BytesIO() of the image
    :rtype: io.BytesIO()
    """
    project_name, folder_name = split_project_path(project)
    image = controller.get_image_bytes(
        project_name=project_name,
        image_name=image_name,
        folder_name=folder_name,
        image_variant=variant,
    ).data
    return image


def copy_image(
    source_project,
    image_name,
    destination_project,
    include_annotations=False,
    copy_annotation_status=False,
    copy_pin=False,
):
    """Copy image to a project. The image's project is the same as destination
    project then the name will be changed to <image_name>_(<num>).<image_ext>,
    where <num> is the next available number deducted from project image list.

    :param source_project: project name plus optional subfolder in the project (e.g., "project1/folder1") or
                           metadata of the project of source project
    :type source_project: str or dict
    :param image_name: image name
    :type image: str
    :param destination_project: project name or metadata of the project of destination project
    :type destination_project: str or dict
    :param include_annotations: enables annotations copy
    :type include_annotations: bool
    :param copy_annotation_status: enables annotations status copy
    :type copy_annotation_status: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    """
    source_project_name, source_folder_name = split_project_path(source_project)

    destination_project, destination_folder = split_project_path(destination_project)

    img_bytes = get_image_bytes(project=source_project, image_name=image_name)
    image_path = destination_folder + image_name

    image_entity = controller.upload_image_to_s3(
        project_name=destination_project, image_path=image_path, image_bytes=img_bytes
    ).data

    del img_bytes

    if copy_annotation_status:
        res = controller.get_image(
            project_name=source_project,
            image_name=image_name,
            folder_path=source_folder_name,
        )
        image_entity.annotation_status_code = res.annotation_status_code

    controller.attach_urls(
        project_name=destination_project,
        files=[image_entity],
        folder_name=destination_folder,
    )

    if include_annotations:
        controller.copy_image_annotation_classes(
            from_project_name=source_project_name,
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
        f"Copied image {source_project_name}/{source_folder_name}"
        f" to {destination_project}/{destination_folder}/{image_name}."
    )


def upload_images_from_public_urls_to_project(
    project,
    img_urls,
    img_names=None,
    annotation_status="NotStarted",
    image_quality_in_editor=None,
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

    if img_names is not None and len(img_names) != len(img_urls):
        raise AppException("Not all image URLs have corresponding names.")

    project_name, folder_name = split_project_path(project)
    existing_images = controller.search_images(
        project_name=project_name, folder_path=folder_name
    ).data
    if not img_names:
        img_names = [os.path.basename(urlparse(url).path) for url in img_urls]

    image_name_url_map = {img_urls[i]: img_names[i] for i in range(len(img_names))}
    duplicate_images = list(
        {image.name for image in existing_images} & set(image_name_url_map.keys())
    )
    images_to_upload = []

    def _upload_image(image_url, image_path) -> str:
        download_response = controller.download_image_from_public_url(
            project_name=project_name, image_url=image_url
        )
        if not download_response.errors:
            upload_response = controller.upload_image_to_s3(
                project_name=project_name,
                image_path=image_path,
                image_bytes=download_response.data,
                folder_name=folder_name,
            )
            if not upload_response.errors:
                images_to_upload.append(upload_response.data)
        else:
            logger.warning(download_response.errors)
        return image_url

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        failed_images = []
        for i, img_url in enumerate(img_urls):
            if img_names[i] not in duplicate_images:
                failed_images.append(
                    executor.submit(_upload_image, img_url, img_names[i])
                )

    for i in range(0, len(images_to_upload), 500):
        controller.upload_images(
            project_name=project_name,
            images=images_to_upload[i : i + 500],  # noqa: E203
            annotation_status=annotation_status,
            image_quality=image_quality_in_editor,
        )

    uploaded_image_names = set(image_name_url_map.keys()) - set(failed_images)
    uploaded_image_urls = [image_name_url_map[name] for name in uploaded_image_names]

    return uploaded_image_urls, uploaded_image_names, duplicate_images, failed_images


def copy_images(
    source_project,
    image_names,
    destination_project,
    include_annotations=True,
    copy_annotation_status=True,
    copy_pin=True,
):
    """Copy images in bulk between folders in a project

    :param source_project: project name or folder path (e.g., "project1/folder1")
    :type source_project: str
    :param image_names: image names. If None, all images from source project will be copied
    :type image: list of str
    :param destination_project: project name or folder path (e.g., "project1/folder2")
    :type destination_project: str
    :param include_annotations: enables annotations copy
    :type include_annotations: bool
    :param copy_annotation_status: enables annotations status copy
    :type copy_annotation_status: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    :return: list of skipped image names
    :rtype: list of strs
    """

    project_name, source_folder_name = split_project_path(source_project)

    _, destination_folder_name = split_project_path(destination_project)

    if not image_names:
        images = controller.search_images(
            project_name=project_name, folder_path=source_folder_name
        )
        image_names = [image.name for image in images]

    res = controller.bulk_copy_images(
        project_name=project_name,
        from_folder_name=source_folder_name,
        to_folder_name=destination_folder_name,
        image_names=image_names,
        include_annotations=include_annotations,
        include_pin=copy_pin,
    )
    skipped_images = res.data
    done_count = len(image_names) - len(skipped_images)
    message_postfix = "{from_path} to {to_path}."
    message_prefix = "Copied images from "
    if done_count > 1 or done_count == 0:
        message_prefix = f"Copied {done_count}/{len(image_names)} images from"
    elif done_count == 1:
        message_prefix = "Copied an image from "
    logger.info(
        message_prefix
        + message_postfix.format(from_path=source_project, to_path=destination_project)
    )

    return skipped_images


def move_images(
    source_project,
    image_names,
    destination_project,
    include_annotations=True,
    copy_annotation_status=True,
    copy_pin=True,
):
    """Move images in bulk between folders in a project

    :param source_project: project name or folder path (e.g., "project1/folder1")
    :type source_project: str
    :param image_names: image names. If None, all images from source project will be moved
    :type image: list of str
    :param destination_project: project name or folder path (e.g., "project1/folder2")
    :type destination_project: str
    :param include_annotations: enables annotations copy
    :type include_annotations: bool
    :param copy_annotation_status: enables annotations status copy
    :type copy_annotation_status: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    :return: list of skipped image names
    :rtype: list of strs
    """
    project_name, source_folder_name = split_project_path(source_project)

    _, destination_folder_name = split_project_path(destination_project)

    if not image_names:
        images = controller.search_images(
            project_name=project_name, folder_path=source_folder_name
        )
        image_names = [image.name for image in images]

    moved_images = controller.bulk_move_images(
        project_name=project_name,
        from_folder_name=source_folder_name,
        to_folder_name=destination_folder_name,
        image_names=image_names,
    ).data
    moved_count = len(moved_images)
    message_postfix = "{from_path} to {to_path}."
    message_prefix = "Copied images from "
    if moved_count > 1 or moved_count == 0:
        message_prefix = f"Moved {moved_count}/{len(image_names)} images from "
    elif moved_count == 1:
        message_prefix = "Moved an image from"

    logger.info(
        message_prefix
        + message_postfix.format(from_path=source_project, to_path=destination_project)
    )

    return len(image_names) - moved_count


def get_project_metadata(
    project,
    include_annotation_classes=False,
    include_settings=False,
    include_workflow=False,
    include_contributors=False,
    include_complete_image_count=False,
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
    project_name, folder_name = split_project_path(project)
    metadata = controller.get_project_metadata(
        project_name,
        include_annotation_classes,
        include_settings,
        include_workflow,
        include_contributors,
        include_complete_image_count,
    )
    metadata = metadata.data
    for elem in "settings", "classes", "workflow":
        if metadata.get(elem):
            metadata[elem] = [
                BaseSerializers(attribute).serialize() for attribute in metadata[elem]
            ]

    if metadata.get("project"):
        metadata["project"] = ProjectSerializer(metadata["project"]).serialize()
    return metadata


def get_project_settings(project):
    """Gets project's settings.

    Return value example: [{ "attribute" : "Brightness", "value" : 10, ...},...]

    :param project: project name or metadata
    :type project: str or dict

    :return: project settings
    :rtype: list of dicts
    """
    project_name, folder_name = split_project_path(project)
    settings = controller.get_project_settings(project_name=project_name)
    settings = [BaseSerializers(attribute).serialize() for attribute in settings.data]
    return settings


def get_project_workflow(project):
    """Gets project's workflow.

    Return value example: [{ "step" : <step_num>, "className" : <annotation_class>, "tool" : <tool_num>, ...},...]

    :param project: project name or metadata
    :type project: str or dict

    :return: project workflow
    :rtype: list of dicts
    """
    project_name, folder_name = split_project_path(project)
    workflow = controller.get_project_workflow(project_name=project_name)
    workflow = [BaseSerializers(attribute).serialize() for attribute in workflow.data]
    return workflow


def search_annotation_classes(project, name_prefix=None):
    """Searches annotation classes by name_prefix (case-insensitive)

    :param project: project name
    :type project: str
    :param name_prefix: name prefix for search. If None all annotation classes
     will be returned
    :type name_prefix: str

    :return: annotation classes of the project
    :rtype: list of dicts
    """
    project_name, folder_name = split_project_path(project)
    classes = controller.search_annotation_classes(project_name, name_prefix)
    classes = [BaseSerializers(attribute).serialize() for attribute in classes.data]
    return classes


def set_project_settings(project, new_settings):
    """Sets project's settings.

    New settings format example: [{ "attribute" : "Brightness", "value" : 10, ...},...]

    :param project: project name or metadata
    :type project: str or dict
    :param new_settings: new settings list of dicts
    :type new_settings: list of dicts

    :return: updated part of project's settings
    :rtype: list of dicts
    """
    project_name, folder_name = split_project_path(project)
    updated = controller.set_project_settings(project_name, new_settings)
    return updated.data


def get_project_default_image_quality_in_editor(project):
    """Gets project's default image quality in editor setting.

    :param project: project name or metadata
    :type project: str or dict

    :return: "original" or "compressed" setting value
    :rtype: str
    """
    project_name, folder_name = split_project_path(project)
    settings = controller.get_project_settings(project_name)
    for setting in settings:
        if setting.attribute == "ImageQuality":
            return setting.value


def set_project_default_image_quality_in_editor(project, image_quality_in_editor):
    """Sets project's default image quality in editor setting.

    :param project: project name or metadata
    :type project: str or dict
    :param image_quality_in_editor: new setting value, should be "original" or "compressed"
    :type image_quality_in_editor: str
    """
    project_name, folder_name = split_project_path(project)
    updated = controller.set_project_settings(
        project_name=project_name,
        new_settings=[{"attribute": "ImageQuality", "value": image_quality_in_editor}],
    )
    return updated.data


def pin_image(project, image_name, pin=True):
    """Pins (or unpins) image

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param pin: sets to pin if True, else unpins image
    :type pin: bool
    """
    project_name, folder_name = split_project_path(project)
    controller.update_image(
        project_name=project_name,
        image_name=image_name,
        folder_name=folder_name,
        is_pinned=int(pin),
    )


def delete_image(project, image_name):
    """Deletes image

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    """
    project_name, _ = split_project_path(project)
    controller.delete_image(image_name=image_name, project_name=project_name)


def get_image_metadata(project, image_names, return_dict_on_single_output=True):
    """Returns image metadata

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str

    :return: metadata of image
    :rtype: dict
    """
    project_name, folder_name = split_project_path(project)
    images = controller.get_image_metadata(project_name, image_names)
    return images.data.json()


def set_images_annotation_statuses(project, image_names, annotation_status):
    """Sets annotation statuses of images

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_names: image names. If None, all the images in the project will be used
    :type image_names: list of str
    :param annotation_status: annotation status to set,
           should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    """
    project_name, folder_name = split_project_path(project)
    controller.set_images_annotation_statuses(
        project_name, folder_name, image_names, annotation_status
    )


def delete_images(project, image_names=None):
    """Delete images in project.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_names: to be deleted images' names. If None, all the images will be deleted
    :type image_names: list of strs
    """
    project_name, folder_name = split_project_path(project)

    controller.delete_images(
        project_name=project_name, folder_name=folder_name, image_names=image_names
    )

    logger.info(
        f"Images deleted in project {project_name}{'' if folder_name else '/' + folder_name}"
    )


def assign_images(project, image_names, user):
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
    project_name, folder_name = split_project_path(project)
    if not folder_name:
        folder_name = "root"
    controller.assign_images(project_name, folder_name, image_names, user)


def unassign_images(project, image_names):
    """Removes assignment of given images for all assignees.With SDK,
    the user can be assigned to a role in the project with the share_project
    function.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_names: list of image unassign
    :type image_names: list of str
    """
    project_name, folder_name = split_project_path(project)

    controller.un_assign_images(
        project_name=project_name, folder_name=folder_name, image_names=image_names
    )


def unassign_folder(project_name, folder_name):
    """Removes assignment of given folder for all assignees.
    With SDK, the user can be assigned to a role in the project
    with the share_project function.

    :param project_name: project name
    :type project_name: str
    :param folder_name: folder name to remove assignees
    :type folder_name: str
    """
    controller.un_assign_folder(project_name=project_name, folder_name=folder_name)


def assign_folder(project_name, folder_name, users):
    """Assigns folder to users. With SDK, the user can be
    assigned to a role in the project with the share_project function.

    :param project_name: project name or metadata of the project
    :type project_name: str or dict
    :param folder_name: folder name to assign
    :type folder_name: str
    :param users: list of user emails
    :type user: list of str
    """
    controller.assign_folder(
        project_name=project_name, folder_name=folder_name, users=users
    )


def share_project(project_name, user, user_role):
    """Share project with user.

    :param project_name: project name
    :type project_name: str
    :param user: user email or metadata of the user to share project with
    :type user: str or dict
    :param user_role: user role to apply, one of Admin , Annotator , QA , Customer , Viewer
    :type user_role: str
    """
    controller.share_project(project_name=project_name, user=user, user_role=user_role)


def unshare_project(project_name, user):
    """Unshare (remove) user from project.

    :param project_name: project name
    :type project_name: str
    :param user: user email or metadata of the user to unshare project
    :type user: str or dict
    """
    controller.unshare_project(project_name=project_name, user=user)


def upload_images_from_google_cloud_to_project(
    project,
    google_project,
    bucket_name,
    folder_path,
    annotation_status="NotStarted",
    image_quality_in_editor=None,
):
    """Uploads all images present in folder_path at bucket_name in google_project to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param google_project: the project name on google cloud, where the bucket resides
    :type google_project: str
    :param bucket_name: the name of the bucket where the images are stored
    :type bucket_name: str
    :param folder_path: path of the folder on the bucket where the images are stored
    :type folder_path: str
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded images' urls, uploaded images' filenames, duplicate images' filenames and not-uploaded images' urls
    :rtype: tuple of list of strs
    """
    uploaded_image_entities = []
    project_name, folder_name = split_project_path(project)

    def _upload_image(image_path: str) -> str:
        with open(image_path, "rb") as image:
            image_bytes = BytesIO(image.read())
            upload_response = controller.upload_image_to_s3(
                project_name=project_name,
                image_path=image_path,
                image_bytes=image_bytes,
                folder_name=folder_name,
            )
            if not upload_response.errors:
                uploaded_image_entities.append(upload_response.data)
            else:
                return image_path

    with tempfile.TemporaryDirectory() as save_dir_name:
        response = controller.download_images_from_google_clout(
            project_name=google_project,
            bucket_name=bucket_name,
            folder_name=folder_path,
            download_path=save_dir_name,
        )
        if response.errors:
            for error in response.errors:
                logger.warning(error)
        images_to_upload = response.data.get("downloaded_images")
        duplicated_images = response.data.get("duplicated_images")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            failed_images = []
            for image_path in enumerate(images_to_upload):
                failed_images.append(executor.submit(_upload_image, image_path))

    for i in range(0, len(images_to_upload), 500):
        controller.upload_images(
            project_name=project_name,
            images=images_to_upload[i : i + 500],
            annotation_status=annotation_status,
            image_quality=image_quality_in_editor,
        )

    uploaded_image_names = [image.name for image in uploaded_image_entities]
    # todo return uploaded images' urls
    return uploaded_image_names, duplicated_images, failed_images


def upload_images_from_azure_blob_to_project(
    project,
    container_name,
    folder_path,
    annotation_status="NotStarted",
    image_quality_in_editor=None,
):
    """Uploads all images present in folder_path at container_name Azure blob storage to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param container_name: container name of the Azure blob storage
    :type container_name: str
    :param folder_path: path of the folder on the bucket where the images are stored
    :type folder_path: str
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded images' urls, uploaded images' filenames, duplicate images' filenames and not-uploaded images' urls
    :rtype: tuple of list of strs
    """
    uploaded_image_entities = []
    project_name, folder_name = split_project_path(project)

    def _upload_image(image_path: str) -> str:
        with open(image_path, "rb") as image:
            image_bytes = BytesIO(image.read())
            upload_response = controller.upload_image_to_s3(
                project_name=project_name,
                image_path=image_path,
                image_bytes=image_bytes,
                folder_name=folder_name,
            )
            if not upload_response.errors:
                uploaded_image_entities.append(upload_response.data)
            else:
                return image_path

    with tempfile.TemporaryDirectory() as save_dir_name:
        response = controller.download_images_from_azure_cloud(
            container_name=container_name,
            folder_name=folder_path,
            download_path=save_dir_name,
        )
        if response.errors:
            for error in response.errors:
                logger.warning(error)
        images_to_upload = response.data.get("downloaded_images")
        duplicated_images = response.data.get("duplicated_images")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            failed_images = []
            for image_path in enumerate(images_to_upload):
                failed_images.append(executor.submit(_upload_image, image_path))

    for i in range(0, len(images_to_upload), 500):
        controller.upload_images(
            project_name=project_name,
            images=images_to_upload[i : i + 500],
            annotation_status=annotation_status,
            image_quality=image_quality_in_editor,
        )

    uploaded_image_names = [image.name for image in uploaded_image_entities]
    # todo return uploaded images' urls
    return uploaded_image_names, duplicated_images, failed_images


def get_image_annotations(project, image_name):
    """Get annotations of the image.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str

    :return: dict object with following keys:
        "annotation_json": dict object of the annotation,
        "annotation_json_filename": filename on server,
        "annotation_mask": mask (for pixel),
        "annotation_mask_filename": mask filename on server
    :rtype: dict
    """
    project_name, folder_name = split_project_path(project)
    res = controller.get_image_annotations(
        project_name=project_name, folder_name=folder_name, image_name=image_name
    )
    return res


def upload_images_from_folder_to_project(
    project,
    folder_path,
    extensions=constances.DEFAULT_IMAGE_EXTENSIONS,
    annotation_status="NotStarted",
    from_s3_bucket=None,
    exclude_file_patterns=constances.DEFAULT_FILE_EXCLUDE_PATTERNS,
    recursive_subfolders=False,
    image_quality_in_editor=None,
):
    """Uploads all images with given extensions from folder_path to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    If an image with existing name already exists in the project it won't be uploaded,
    and its path will be appended to the third member of return value of this
    function.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param folder_path: from which folder to upload the images
    :type folder_path: Pathlike (str or Path)
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
    uploaded_image_entities = []
    project_name, folder_name = split_project_path(project)

    def _upload_local_image(image_path: str) -> str:
        with open(image_path, "rb") as image:
            image_bytes = BytesIO(image.read())
            upload_response = controller.upload_image_to_s3(
                project_name=project_name,
                image_path=image_path,
                image_bytes=image_bytes,
                folder_name=folder_name,
            )
            if not upload_response.errors:
                uploaded_image_entities.append(upload_response.data)
            else:
                return image_path

    def _upload_s3_image(image_path: str) -> str:
        try:
            image_bytes = controller.get_image_from_s3(
                s3_bucket=from_s3_bucket, image_path=image_path
            ).data
        except AppValidationException as e:
            logger.warning(e)
            return image_path
        upload_response = controller.upload_image_to_s3(
            project_name=project_name,
            image_path=image_path,
            image_bytes=image_bytes,
            folder_name=folder_name,
        )
        if not response.errors:
            uploaded_image_entities.append(upload_response.data)
        else:
            return image_path

    paths = []
    if from_s3_bucket is None:
        for extension in extensions:
            if recursive_subfolders:
                paths += list(Path(folder_path).rglob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    paths += list(Path(folder_path).rglob(f"*.{extension.upper()}"))
            else:
                paths += list(Path(folder_path).glob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    paths += list(Path(folder_path).glob(f"*.{extension.upper()}"))

    else:
        s3_client = boto3.client("s3")
        paginator = s3_client.get_paginator("list_objects_v2")
        response_iterator = paginator.paginate(
            Bucket=from_s3_bucket, Prefix=folder_path
        )
        for response in response_iterator:
            for object_data in response["Contents"]:
                key = object_data["Key"]
                if not recursive_subfolders and "/" in key[len(folder_path) + 1 :]:
                    continue
                for extension in extensions:
                    if key.endswith(f".{extension.lower()}") or key.endswith(
                        f".{extension.upper()}"
                    ):
                        paths.append(key)
                        break

    filtered_paths = []
    for path in paths:
        not_in_exclude_list = [x not in Path(path).name for x in exclude_file_patterns]
        if all(not_in_exclude_list):
            filtered_paths.append(path)

    duplication_counter = Counter(filtered_paths)
    images_to_upload, duplicated_images = (
        set(filtered_paths),
        [item for item in duplication_counter if duplication_counter[item] > 1],
    )
    upload_method = _upload_s3_image if from_s3_bucket else _upload_local_image
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        failed_images = []
        for image_path in enumerate(images_to_upload):
            failed_images.append(executor.submit(upload_method, image_path))

    for i in range(0, len(uploaded_image_entities), 500):
        controller.upload_images(
            project_name=project_name,
            images=uploaded_image_entities[i : i + 500],  # noqa: E203
            annotation_status=annotation_status,
            image_quality=image_quality_in_editor,
        )

    return (
        [image.path for image in uploaded_image_entities],
        duplicated_images,
        failed_images,
    )


def get_project_image_count(project, with_all_subfolders=False):
    """Returns number of images in the project.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param with_all_subfolders: enables recursive folder counting
    :type with_all_subfolders: bool

    :return: number of images in the project
    :rtype: int
    """

    project_name, folder_name = split_project_path(project)

    response = controller.get_project_image_count(
        project_name=project_name,
        folder_name=folder_name,
        with_all_subfolders=with_all_subfolders,
    )
    return response.data


def get_image_preannotations(project, image_name):
    """Get pre-annotations of the image. Only works for "vector" projects.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str

    :return: dict object with following keys:
        "preannotation_json": dict object of the annotation,
        "preannotation_json_filename": filename on server,
        "preannotation_mask": mask (for pixel),
        "preannotation_mask_filename": mask filename on server
    :rtype: dict
    """
    project_name, folder_name = split_project_path(project)
    res = controller.get_image_pre_annotations(
        project_name=project_name, folder_name=folder_name, image_name=image_name
    )
    return res.data


def download_image_annotations(project, image_name, local_dir_path):
    """Downloads annotations of the image (JSON and mask if pixel type project)
    to local_dir_path.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param local_dir_path: local directory path to download to
    :type local_dir_path: Pathlike (str or Path)

    :return: paths of downloaded annotations
    :rtype: tuple
    """
    project_name, folder_name = split_project_path(project)
    res = controller.download_image_annotations(
        project_name=project_name,
        folder_name=folder_name,
        image_name=image_name,
        destination=local_dir_path,
    )
    return res.data


def download_image_preannotations(project, image_name, local_dir_path):
    """Downloads pre-annotations of the image to local_dir_path.
    Only works for "vector" projects.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param local_dir_path: local directory path to download to
    :type local_dir_path: Pathlike (str or Path)

    :return: paths of downloaded pre-annotations
    :rtype: tuple
    """
    project_name, folder_name = split_project_path(project)
    res = controller.download_image_pre_annotations(
        project_name=project_name,
        folder_name=folder_name,
        image_name=image_name,
        destination=local_dir_path,
    )
    return res.data


def get_exports(project, return_metadata=False):
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


def upload_images_from_s3_bucket_to_project(
    project,
    accessKeyId,
    secretAccessKey,
    bucket_name,
    folder_path,
    image_quality_in_editor=None,
):
    """Uploads all images from AWS S3 bucket to the project.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param accessKeyId: AWS S3 access key ID
    :type accessKeyId: str
    :param secretAccessKey: AWS S3 secret access key
    :type secretAccessKey: str
    :param bucket_name: AWS S3 bucket
    :type bucket_name: str
    :param folder_path: from which folder to upload the images
    :type folder_path: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str
    """
    project_name, folder_name = split_project_path(project)
    controller.backend_upload_from_s3(
        project_name=project_name,
        folder_name=folder_name,
        folder_path=folder_path,
        access_key=accessKeyId,
        secret_key=secretAccessKey,
        bucket_name=bucket_name,
        image_quality=image_quality_in_editor,
    )


def prepare_export(
    project,
    folder_names=None,
    annotation_statuses=None,
    include_fuse=False,
    only_pinned=False,
):
    """Prepare annotations and classes.json for export. Original and fused images for images with
    annotations can be included with include_fuse flag.

    :param project: project name
    :type project: str
    :param folder_names: names of folders to include in the export. If None, whole project will be exported
    :type folder_names: list of str
    :param annotation_statuses: images with which status to include, if None, [ "InProgress", "QualityCheck", "Returned", "Completed"] will be chose
           list elements should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_statuses: list of strs
    :param include_fuse: enables fuse images in the export
    :type include_fuse: bool
    :param only_pinned: enable only pinned output in export. This option disables all other types of output.
    :type only_pinned: bool

    :return: metadata object of the prepared export
    :rtype: dict
    """
    project_name = project
    project = controller.search_project(project_name).data[0]
    response = controller.prepare_export(
        project=project,
        folder_names=folder_names,
        include_fuse=include_fuse,
        only_pinned=only_pinned,
        annotation_statuses=annotation_statuses,
    )
    return response.data


def upload_videos_from_folder_to_project(
    project,
    folder_path,
    extensions=constances.DEFAULT_VIDEO_EXTENSIONS,
    exclude_file_patterns=(),
    recursive_subfolders=False,
    target_fps=None,
    start_time=0.0,
    end_time=None,
    annotation_status="NotStarted",
    image_quality_in_editor=None,
):
    """Uploads image frames from all videos with given extensions from folder_path to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param folder_path: from which folder to upload the videos
    :type folder_path: Pathlike (str or Path)
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

    project_name, folder_name = split_project_path(project)

    uploaded_image_entities = []
    failed_images = []

    def _upload_image(image_path: str) -> str:
        with open(image_path, "rb") as image:
            image_bytes = BytesIO(image.read())
            upload_response = controller.upload_image_to_s3(
                project_name=project_name,
                image_path=image_path,
                image_bytes=image_bytes,
                folder_name=folder_name,
            )
            if not upload_response.errors:
                uploaded_image_entities.append(upload_response.data)
            else:
                return image_path

    video_paths = []
    for extension in extensions:
        if not recursive_subfolders:
            video_paths += list(Path(folder_path).glob(f"*.{extension.lower()}"))
            if os.name != "nt":
                video_paths += list(Path(folder_path).glob(f"*.{extension.upper()}"))
        else:
            video_paths += list(Path(folder_path).rglob(f"*.{extension.lower()}"))
            if os.name != "nt":
                video_paths += list(Path(folder_path).rglob(f"*.{extension.upper()}"))
    filtered_paths = []
    video_paths = [str(path) for path in video_paths]
    for path in video_paths:
        not_in_exclude_list = [x not in Path(path).name for x in exclude_file_patterns]
        if all(not_in_exclude_list):
            filtered_paths.append(path)
    for path in video_paths:
        with tempfile.TemporaryDirectory() as temp_path:
            res = controller.extract_video_frames(
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
            if not res.errors:
                extracted_frame_paths = res.data
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    for image_path in extracted_frame_paths:
                        failed_images.append(executor.submit(_upload_image, image_path))

    for i in range(0, len(uploaded_image_entities), 500):
        controller.upload_images(
            project_name=project_name,
            images=uploaded_image_entities[i : i + 500],  # noqa: E203
            annotation_status=annotation_status,
            image_quality=image_quality_in_editor,
        )
    uploaded_images = [
        image.path
        for image in uploaded_image_entities
        if image.name not in failed_images
    ]
    return uploaded_images, failed_images


def upload_video_to_project(
    project,
    video_path,
    target_fps=None,
    start_time=0.0,
    end_time=None,
    annotation_status="NotStarted",
    image_quality_in_editor=None,
):
    """Uploads image frames from video to platform. Uploaded images will have
    names "<video_name>_<frame_no>.jpg".

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param video_path: video to upload
    :type video_path: Pathlike (str or Path)
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

    project_name, folder_name = split_project_path(project)

    uploaded_image_entities = []
    failed_images = []

    def _upload_image(image_path: str) -> str:
        with open(image_path, "rb") as image:
            image_bytes = BytesIO(image.read())
            upload_response = controller.upload_image_to_s3(
                project_name=project_name,
                image_path=image_path,
                image_bytes=image_bytes,
                folder_name=folder_name,
            )
            if not upload_response.errors:
                uploaded_image_entities.append(upload_response.data)
            else:
                return image_path

    with tempfile.TemporaryDirectory() as temp_path:
        res = controller.extract_video_frames(
            project_name=project_name,
            folder_name=folder_name,
            video_path=video_path,
            extract_path=temp_path,
            target_fps=target_fps,
            start_time=start_time,
            end_time=end_time,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        )
        if not res.errors:
            extracted_frame_paths = res.data
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                for image_path in extracted_frame_paths:
                    failed_images.append(executor.submit(_upload_image, image_path))

    for i in range(0, len(uploaded_image_entities), 500):
        controller.upload_images(
            project_name=project_name,
            images=uploaded_image_entities[i : i + 500],  # noqa: E203
            annotation_status=annotation_status,
            image_quality=image_quality_in_editor,
        )
    uploaded_images = [
        image.name
        for image in uploaded_image_entities
        if image.name not in failed_images
    ]
    return uploaded_images


def create_annotation_class(project, name, color, attribute_groups=None):
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
    response = controller.create_annotation_class(
        project_name=project, name=name, color=color, attribute_groups=attribute_groups
    )
    return response.data.to_dict()


def delete_annotation_class(project, annotation_class):
    """Deletes annotation class from project

    :param project: project name
    :type project: str
    :param annotation_class: annotation class name or  metadata
    :type annotation_class: str or dict
    """
    controller.delete_annotation_class(
        project_name=project, annotation_class_name=annotation_class
    )


def get_annotation_class_metadata(project, annotation_class_name):
    """Returns annotation class metadata

    :param project: project name
    :type project: str
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str

    :return: metadata of annotation class
    :rtype: dict
    """
    response = controller.get_annotation_class(
        project_name=project, annotation_class_name=annotation_class_name
    )
    return response.data.to_dict()


def download_annotation_classes_json(project, folder):
    """Downloads project classes.json to folder

    :param project: project name
    :type project: str
    :param folder: folder to download to
    :type folder: Pathlike (str or Path)

    :return: path of the download file
    :rtype: str
    """
    response = controller.download_annotation_classes(
        project_name=project, download_path=folder
    )
    return response.data


def create_annotation_classes_from_classes_json(
    project, classes_json, from_s3_bucket=False
):
    """Creates annotation classes in project from a SuperAnnotate format
    annotation classes.json.

    :param project: project name
    :type project: str
    :param classes_json: JSON itself or path to the JSON file
    :type classes_json: list or Pathlike (str or Path)
    :param from_s3_bucket: AWS S3 bucket to use. If None then classes_json is in local filesystem
    :type from_s3_bucket: bool

    :return: list of created annotation class metadatas
    :rtype: list of dicts
    """
    annotation_classes = []
    if not isinstance(classes_json, list):
        if from_s3_bucket:
            # TODO:
            pass
        else:
            annotation_classes = json.load(open(classes_json))
    else:
        annotation_classes = classes_json
    response = controller.create_annotation_classes(
        project_name=project, annotation_classes=annotation_classes,
    )
    return response.data


def move_image(
        source_project,
        image_name,
        destination_project,
        include_annotations=True,
        copy_annotation_status=True,
        copy_pin=True
):
    """Move image from source_project to destination_project. source_project
    and destination_project cannot be the same.

    :param source_project: project name or metadata of the project of source project
    :type source_project: str or dict
    :param image_name: image name
    :type image: str
    :param destination_project: project name or metadata of the project of destination project
    :type destination_project: str or dict
    :param include_annotations: enables annotations move
    :type include_annotations: bool
    :param copy_annotation_status: enables annotations status copy
    :type copy_annotation_status: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    """

    source_project_name, source_folder_name = split_project_path(source_project)

    destination_project, destination_folder = split_project_path(destination_project)

    img_bytes = get_image_bytes(project=source_project, image_name=image_name)
    image_path = destination_folder + image_name

    image_entity = controller.upload_image_to_s3(
        project_name=destination_project, image_path=image_path, image_bytes=img_bytes
    ).data

    del img_bytes

    if copy_annotation_status:
        res = controller.get_image(
            project_name=source_project,
            image_name=image_name,
            folder_path=source_folder_name,
        )
        image_entity.annotation_status_code = res.annotation_status_code

    controller.attach_urls(
        project_name=destination_project,
        files=[image_entity],
        folder_name=destination_folder,
    )

    if include_annotations:
        controller.copy_image_annotation_classes(
            from_project_name=source_project_name,
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

    controller.delete_image(image_name,source_project_name)




def create_fuse_image(
    image, classes_json, project_type, in_memory=False, output_overlay=False
):
    """Creates fuse for locally located image and annotations

    :param image: path to image
    :type image: str or Pathlike
    :param image_name: annotation classes or path to their JSON
    :type image: list or Pathlike
    :param project_type: project type, "Vector" or "Pixel"
    :type project_type: str
    :param in_memory: enables pillow Image return instead of saving the image
    :type in_memory: bool

    :return: path to created fuse image or pillow Image object if in_memory enabled
    :rtype: str of PIL.Image
    """

    response = controller.create_fuse_image(
        image_path=image,
        project_type=project_type,
        in_memory=in_memory,
        generate_overlay=output_overlay,
    )

    return response.data


def download_image(
    project,
    image_name,
    local_dir_path=".",
    include_annotations=False,
    include_fuse=False,
    include_overlay=False,
    variant="original",
):
    """Downloads the image (and annotation if not None) to local_dir_path

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param local_dir_path: where to download the image
    :type local_dir_path: Pathlike (str or Path)
    :param include_annotations: enables annotation download with the image
    :type include_annotations: bool
    :param include_fuse: enables fuse image download with the image
    :type include_fuse: bool
    :param variant: which resolution to download, can be 'original' or 'lores'
     (low resolution used in web editor)
    :type variant: str

    :return: paths of downloaded image and annotations if included
    :rtype: tuple
    """
    project_name, folder_name = split_project_path(project)
    response = controller.download_image(
        project_name=project_name,
        folder_name=folder_name,
        image_name=image_name,
        download_path=local_dir_path,
        image_variant=variant,
        include_annotations=include_annotations,
        include_fuse=include_fuse,
        include_overlay=include_overlay,
    )
    return response.data
