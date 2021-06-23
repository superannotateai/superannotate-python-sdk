import logging
from pathlib import Path

import lib.core as constances
from lib.app.exceptions import UserInputError
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
    path = Path(project)
    if len(path.parts) > 3:
        raise UserInputError("There can be no subfolders in the project")
    elif len(path.parts) == 2:
        project_name, folder_name = path.parts
    else:
        project_name, folder_name = path.name, None

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


def rename_project(project,new_name):
    """Renames the project

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param new_name: project's new name
    :type new_name: str
    """
    controller.update_project(name=project, project_data={"name": new_name})
