import concurrent.futures
import logging
import os
from urllib.parse import urlparse

import lib.core as constances
from lib.app.exceptions import EmptyOutputError
from lib.app.helpers import split_project_path
from lib.app.serializers import BaseSerializers
from lib.app.serializers import ImageSerializer
from lib.app.serializers import ProjectSerializer
from lib.app.serializers import TeamSerializer
from lib.core.exceptions import AppException
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

    result = controller.create_folder(
        project_name=project, folder_name=folder_name
    ).data
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
    image = controller.download_image(
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
        message_prefix = f"Moved an image from"

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
    controller.set_images_annotation_statuses(project_name,folder_name,image_names,annotation_status)


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
