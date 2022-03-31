import logging.config
import os
import sys

import requests
import superannotate.lib.core as constances
from packaging.version import parse
from superannotate.lib import get_default_controller
from superannotate.lib.app.analytics.class_analytics import class_distribution
from superannotate.lib.app.exceptions import AppException
from superannotate.lib.app.input_converters.conversion import convert_json_version
from superannotate.lib.app.input_converters.conversion import convert_project_type
from superannotate.lib.app.input_converters.conversion import export_annotation
from superannotate.lib.app.input_converters.conversion import import_annotation
from superannotate.lib.app.interface.sdk_interface import add_annotation_bbox_to_image
from superannotate.lib.app.interface.sdk_interface import (
    add_annotation_comment_to_image,
)
from superannotate.lib.app.interface.sdk_interface import add_annotation_point_to_image
from superannotate.lib.app.interface.sdk_interface import add_contributors_to_project
from superannotate.lib.app.interface.sdk_interface import aggregate_annotations_as_df
from superannotate.lib.app.interface.sdk_interface import assign_folder
from superannotate.lib.app.interface.sdk_interface import assign_images
from superannotate.lib.app.interface.sdk_interface import (
    attach_document_urls_to_project,
)
from superannotate.lib.app.interface.sdk_interface import attach_image_urls_to_project
from superannotate.lib.app.interface.sdk_interface import (
    attach_items_from_integrated_storage,
)
from superannotate.lib.app.interface.sdk_interface import attach_video_urls_to_project
from superannotate.lib.app.interface.sdk_interface import benchmark
from superannotate.lib.app.interface.sdk_interface import clone_project
from superannotate.lib.app.interface.sdk_interface import consensus
from superannotate.lib.app.interface.sdk_interface import copy_image
from superannotate.lib.app.interface.sdk_interface import copy_images
from superannotate.lib.app.interface.sdk_interface import create_annotation_class
from superannotate.lib.app.interface.sdk_interface import (
    create_annotation_classes_from_classes_json,
)
from superannotate.lib.app.interface.sdk_interface import create_folder
from superannotate.lib.app.interface.sdk_interface import create_project
from superannotate.lib.app.interface.sdk_interface import create_project_from_metadata
from superannotate.lib.app.interface.sdk_interface import delete_annotation_class
from superannotate.lib.app.interface.sdk_interface import delete_annotations
from superannotate.lib.app.interface.sdk_interface import delete_folders
from superannotate.lib.app.interface.sdk_interface import delete_images
from superannotate.lib.app.interface.sdk_interface import delete_project
from superannotate.lib.app.interface.sdk_interface import (
    download_annotation_classes_json,
)
from superannotate.lib.app.interface.sdk_interface import download_export
from superannotate.lib.app.interface.sdk_interface import download_image
from superannotate.lib.app.interface.sdk_interface import download_image_annotations
from superannotate.lib.app.interface.sdk_interface import download_model
from superannotate.lib.app.interface.sdk_interface import get_annotations
from superannotate.lib.app.interface.sdk_interface import get_annotations_per_frame
from superannotate.lib.app.interface.sdk_interface import get_exports
from superannotate.lib.app.interface.sdk_interface import get_folder_metadata
from superannotate.lib.app.interface.sdk_interface import get_image_metadata
from superannotate.lib.app.interface.sdk_interface import get_integrations
from superannotate.lib.app.interface.sdk_interface import get_item_metadata
from superannotate.lib.app.interface.sdk_interface import (
    get_project_and_folder_metadata,
)
from superannotate.lib.app.interface.sdk_interface import get_project_image_count
from superannotate.lib.app.interface.sdk_interface import get_project_metadata
from superannotate.lib.app.interface.sdk_interface import get_project_settings
from superannotate.lib.app.interface.sdk_interface import get_project_workflow
from superannotate.lib.app.interface.sdk_interface import get_team_metadata
from superannotate.lib.app.interface.sdk_interface import init
from superannotate.lib.app.interface.sdk_interface import invite_contributors_to_team
from superannotate.lib.app.interface.sdk_interface import move_images
from superannotate.lib.app.interface.sdk_interface import pin_image
from superannotate.lib.app.interface.sdk_interface import prepare_export
from superannotate.lib.app.interface.sdk_interface import query
from superannotate.lib.app.interface.sdk_interface import rename_project
from superannotate.lib.app.interface.sdk_interface import run_prediction
from superannotate.lib.app.interface.sdk_interface import search_annotation_classes
from superannotate.lib.app.interface.sdk_interface import search_folders
from superannotate.lib.app.interface.sdk_interface import search_images
from superannotate.lib.app.interface.sdk_interface import search_images_all_folders
from superannotate.lib.app.interface.sdk_interface import search_items
from superannotate.lib.app.interface.sdk_interface import search_models
from superannotate.lib.app.interface.sdk_interface import search_projects
from superannotate.lib.app.interface.sdk_interface import search_team_contributors
from superannotate.lib.app.interface.sdk_interface import set_auth_token
from superannotate.lib.app.interface.sdk_interface import set_image_annotation_status
from superannotate.lib.app.interface.sdk_interface import set_images_annotation_statuses
from superannotate.lib.app.interface.sdk_interface import (
    set_project_default_image_quality_in_editor,
)
from superannotate.lib.app.interface.sdk_interface import set_project_workflow
from superannotate.lib.app.interface.sdk_interface import share_project
from superannotate.lib.app.interface.sdk_interface import unassign_folder
from superannotate.lib.app.interface.sdk_interface import unassign_images
from superannotate.lib.app.interface.sdk_interface import (
    upload_annotations_from_folder_to_project,
)
from superannotate.lib.app.interface.sdk_interface import upload_image_annotations
from superannotate.lib.app.interface.sdk_interface import upload_image_to_project
from superannotate.lib.app.interface.sdk_interface import (
    upload_images_from_folder_to_project,
)
from superannotate.lib.app.interface.sdk_interface import upload_images_to_project
from superannotate.lib.app.interface.sdk_interface import (
    upload_preannotations_from_folder_to_project,
)
from superannotate.lib.app.interface.sdk_interface import upload_priority_scores
from superannotate.lib.app.interface.sdk_interface import upload_video_to_project
from superannotate.lib.app.interface.sdk_interface import (
    upload_videos_from_folder_to_project,
)
from superannotate.lib.app.interface.sdk_interface import validate_annotations
from superannotate.logger import get_default_logger
from superannotate.version import __version__


controller = get_default_controller()


__all__ = [
    "__version__",
    "controller",
    "constances",
    # Utils
    "AppException",
    "validate_annotations",
    #
    "init",
    "set_auth_token",
    # analytics
    "class_distribution",
    "aggregate_annotations_as_df",
    "get_exports",
    # annotations
    "get_annotations",
    "get_annotations_per_frame",
    # integrations
    "get_integrations",
    "attach_items_from_integrated_storage",
    # converters
    "convert_json_version",
    "import_annotation",
    "export_annotation",
    "convert_project_type",
    # Teams Section
    "get_team_metadata",
    "search_team_contributors",
    # Projects Section
    "create_project_from_metadata",
    "get_project_settings",
    "get_project_metadata",
    "get_project_workflow",
    "set_project_workflow",
    "search_projects",
    "create_project",
    "clone_project",
    "share_project",
    "delete_project",
    "rename_project",
    "upload_priority_scores",
    # Images Section
    "search_images",
    "copy_image",
    # Folders Section
    "create_folder",
    "get_folder_metadata",
    "delete_folders",
    "get_project_and_folder_metadata",
    "search_folders",
    "assign_folder",
    "unassign_folder",
    # Items Section
    "get_item_metadata",
    "search_items",
    "query",
    # Image Section
    "copy_images",
    "move_images",
    "delete_images",
    "download_image",
    "pin_image",
    "get_image_metadata",
    "get_project_image_count",
    "search_images_all_folders",
    "assign_images",
    "unassign_images",
    "download_image_annotations",
    "delete_annotations",
    "upload_image_to_project",
    "upload_image_annotations",
    "upload_images_from_folder_to_project",
    "attach_image_urls_to_project",
    "attach_video_urls_to_project",
    "attach_document_urls_to_project",
    # Video Section
    "upload_videos_from_folder_to_project",
    # Annotation Section
    "create_annotation_class",
    "delete_annotation_class",
    "prepare_export",
    "download_export",
    "set_images_annotation_statuses",
    "add_annotation_bbox_to_image",
    "add_annotation_point_to_image",
    "add_annotation_comment_to_image",
    "search_annotation_classes",
    "create_annotation_classes_from_classes_json",
    "upload_annotations_from_folder_to_project",
    "upload_preannotations_from_folder_to_project",
    "download_annotation_classes_json",
    "set_project_default_image_quality_in_editor",
    "run_prediction",
    "search_models",
    "download_model",
    "set_image_annotation_status",
    "benchmark",
    "consensus",
    "upload_video_to_project",
    "upload_images_to_project",
    "add_contributors_to_project",
    "invite_contributors_to_team",
]

__author__ = "Superannotate"

WORKING_DIR = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(WORKING_DIR)
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logger = get_default_logger()


def log_version_info():
    local_version = parse(__version__)
    if local_version.is_prerelease:
        logger.info(constances.PACKAGE_VERSION_INFO_MESSAGE.format(__version__))
    req = requests.get("https://pypi.python.org/pypi/superannotate/json")
    if req.ok:
        releases = req.json().get("releases", [])
        pip_version = parse("0")
        for release in releases:
            ver = parse(release)
            if not ver.is_prerelease or local_version.is_prerelease:
                pip_version = max(pip_version, ver)
        if pip_version.major > local_version.major:
            logger.warning(
                constances.PACKAGE_VERSION_MAJOR_UPGRADE.format(
                    local_version, pip_version
                )
            )
        elif pip_version > local_version:
            logger.warning(
                constances.PACKAGE_VERSION_UPGRADE.format(local_version, pip_version)
            )


if not os.environ.get("SA_VERSION_CHECK", "True").lower() == "false":
    log_version_info()
