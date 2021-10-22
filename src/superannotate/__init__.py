import logging.config
import os
import sys

from superannotate.lib.app.analytics.class_analytics import attribute_distribution
from superannotate.lib.app.analytics.class_analytics import class_distribution
from superannotate.lib.app.annotation_helpers import add_annotation_bbox_to_json
from superannotate.lib.app.annotation_helpers import add_annotation_comment_to_json
from superannotate.lib.app.annotation_helpers import add_annotation_cuboid_to_json
from superannotate.lib.app.annotation_helpers import add_annotation_ellipse_to_json
from superannotate.lib.app.annotation_helpers import add_annotation_point_to_json
from superannotate.lib.app.annotation_helpers import add_annotation_polygon_to_json
from superannotate.lib.app.annotation_helpers import add_annotation_polyline_to_json
from superannotate.lib.app.annotation_helpers import add_annotation_template_to_json
from superannotate.lib.app.common import image_path_to_annotation_paths
from superannotate.lib.app.exceptions import AppException
from superannotate.lib.app.input_converters.conversion import coco_split_dataset
from superannotate.lib.app.input_converters.conversion import convert_json_version
from superannotate.lib.app.input_converters.conversion import convert_project_type
from superannotate.lib.app.input_converters.conversion import export_annotation
from superannotate.lib.app.input_converters.conversion import import_annotation
from superannotate.lib.app.input_converters.df_converter import df_to_annotations
from superannotate.lib.app.input_converters.df_converter import (
    filter_annotation_instances,
)
from superannotate.lib.app.input_converters.df_converter import (
    filter_images_by_comments,
)
from superannotate.lib.app.input_converters.df_converter import filter_images_by_tags
from superannotate.lib.app.input_converters.dicom_converter import dicom_to_rgb_sequence
from superannotate.lib.app.interface.sdk_interface import add_annotation_bbox_to_image
from superannotate.lib.app.interface.sdk_interface import (
    add_annotation_comment_to_image,
)
from superannotate.lib.app.interface.sdk_interface import add_annotation_cuboid_to_image
from superannotate.lib.app.interface.sdk_interface import (
    add_annotation_ellipse_to_image,
)
from superannotate.lib.app.interface.sdk_interface import add_annotation_point_to_image
from superannotate.lib.app.interface.sdk_interface import (
    add_annotation_polygon_to_image,
)
from superannotate.lib.app.interface.sdk_interface import (
    add_annotation_polyline_to_image,
)
from superannotate.lib.app.interface.sdk_interface import (
    add_annotation_template_to_image,
)
from superannotate.lib.app.interface.sdk_interface import aggregate_annotations_as_df
from superannotate.lib.app.interface.sdk_interface import assign_folder
from superannotate.lib.app.interface.sdk_interface import assign_images
from superannotate.lib.app.interface.sdk_interface import (
    attach_document_urls_to_project,
)
from superannotate.lib.app.interface.sdk_interface import attach_image_urls_to_project
from superannotate.lib.app.interface.sdk_interface import attach_video_urls_to_project
from superannotate.lib.app.interface.sdk_interface import benchmark
from superannotate.lib.app.interface.sdk_interface import clone_project
from superannotate.lib.app.interface.sdk_interface import consensus
from superannotate.lib.app.interface.sdk_interface import controller
from superannotate.lib.app.interface.sdk_interface import copy_image
from superannotate.lib.app.interface.sdk_interface import copy_images
from superannotate.lib.app.interface.sdk_interface import create_annotation_class
from superannotate.lib.app.interface.sdk_interface import (
    create_annotation_classes_from_classes_json,
)
from superannotate.lib.app.interface.sdk_interface import create_folder
from superannotate.lib.app.interface.sdk_interface import create_fuse_image
from superannotate.lib.app.interface.sdk_interface import create_project
from superannotate.lib.app.interface.sdk_interface import create_project_from_metadata
from superannotate.lib.app.interface.sdk_interface import delete_annotation_class
from superannotate.lib.app.interface.sdk_interface import delete_annotations
from superannotate.lib.app.interface.sdk_interface import (
    delete_contributor_to_team_invitation,
)
from superannotate.lib.app.interface.sdk_interface import delete_folders
from superannotate.lib.app.interface.sdk_interface import delete_image
from superannotate.lib.app.interface.sdk_interface import delete_images
from superannotate.lib.app.interface.sdk_interface import delete_model
from superannotate.lib.app.interface.sdk_interface import delete_project
from superannotate.lib.app.interface.sdk_interface import (
    download_annotation_classes_json,
)
from superannotate.lib.app.interface.sdk_interface import download_export
from superannotate.lib.app.interface.sdk_interface import download_image
from superannotate.lib.app.interface.sdk_interface import download_image_annotations
from superannotate.lib.app.interface.sdk_interface import download_image_preannotations
from superannotate.lib.app.interface.sdk_interface import download_model
from superannotate.lib.app.interface.sdk_interface import get_annotation_class_metadata
from superannotate.lib.app.interface.sdk_interface import get_exports
from superannotate.lib.app.interface.sdk_interface import get_folder_metadata
from superannotate.lib.app.interface.sdk_interface import get_image_annotations
from superannotate.lib.app.interface.sdk_interface import get_image_bytes
from superannotate.lib.app.interface.sdk_interface import get_image_metadata
from superannotate.lib.app.interface.sdk_interface import get_image_preannotations
from superannotate.lib.app.interface.sdk_interface import (
    get_project_and_folder_metadata,
)
from superannotate.lib.app.interface.sdk_interface import (
    get_project_default_image_quality_in_editor,
)
from superannotate.lib.app.interface.sdk_interface import get_project_image_count
from superannotate.lib.app.interface.sdk_interface import get_project_metadata
from superannotate.lib.app.interface.sdk_interface import get_project_settings
from superannotate.lib.app.interface.sdk_interface import get_project_workflow
from superannotate.lib.app.interface.sdk_interface import get_team_metadata
from superannotate.lib.app.interface.sdk_interface import init
from superannotate.lib.app.interface.sdk_interface import invite_contributor_to_team
from superannotate.lib.app.interface.sdk_interface import move_image
from superannotate.lib.app.interface.sdk_interface import move_images
from superannotate.lib.app.interface.sdk_interface import pin_image
from superannotate.lib.app.interface.sdk_interface import plot_model_metrics
from superannotate.lib.app.interface.sdk_interface import prepare_export
from superannotate.lib.app.interface.sdk_interface import rename_folder
from superannotate.lib.app.interface.sdk_interface import rename_project
from superannotate.lib.app.interface.sdk_interface import run_prediction
from superannotate.lib.app.interface.sdk_interface import run_segmentation
from superannotate.lib.app.interface.sdk_interface import run_training
from superannotate.lib.app.interface.sdk_interface import search_annotation_classes
from superannotate.lib.app.interface.sdk_interface import search_folders
from superannotate.lib.app.interface.sdk_interface import search_images
from superannotate.lib.app.interface.sdk_interface import search_images_all_folders
from superannotate.lib.app.interface.sdk_interface import search_models
from superannotate.lib.app.interface.sdk_interface import search_projects
from superannotate.lib.app.interface.sdk_interface import search_team_contributors
from superannotate.lib.app.interface.sdk_interface import set_auth_token
from superannotate.lib.app.interface.sdk_interface import set_image_annotation_status
from superannotate.lib.app.interface.sdk_interface import set_images_annotation_statuses
from superannotate.lib.app.interface.sdk_interface import (
    set_project_default_image_quality_in_editor,
)
from superannotate.lib.app.interface.sdk_interface import set_project_settings
from superannotate.lib.app.interface.sdk_interface import set_project_workflow
from superannotate.lib.app.interface.sdk_interface import share_project
from superannotate.lib.app.interface.sdk_interface import stop_model_training
from superannotate.lib.app.interface.sdk_interface import unassign_folder
from superannotate.lib.app.interface.sdk_interface import unassign_images
from superannotate.lib.app.interface.sdk_interface import unshare_project
from superannotate.lib.app.interface.sdk_interface import (
    upload_annotations_from_folder_to_project,
)
from superannotate.lib.app.interface.sdk_interface import upload_image_annotations
from superannotate.lib.app.interface.sdk_interface import upload_image_to_project
from superannotate.lib.app.interface.sdk_interface import (
    upload_images_from_folder_to_project,
)
from superannotate.lib.app.interface.sdk_interface import (
    upload_images_from_public_urls_to_project,
)
from superannotate.lib.app.interface.sdk_interface import (
    upload_images_from_s3_bucket_to_project,
)
from superannotate.lib.app.interface.sdk_interface import upload_images_to_project
from superannotate.lib.app.interface.sdk_interface import (
    upload_preannotations_from_folder_to_project,
)
from superannotate.lib.app.interface.sdk_interface import upload_video_to_project
from superannotate.lib.app.interface.sdk_interface import (
    upload_videos_from_folder_to_project,
)
from superannotate.lib.app.interface.sdk_interface import validate_annotations
from superannotate.version import __version__


__all__ = [
    "__version__",
    "controller",
    # Utils
    "AppException",
    "validate_annotations",
    #
    "init",
    "set_auth_token",
    # analytics
    "attribute_distribution",
    "class_distribution",
    "aggregate_annotations_as_df",
    "get_exports",
    # common
    "df_to_annotations",
    "image_path_to_annotation_paths",
    # converters
    "dicom_to_rgb_sequence",
    "coco_split_dataset",
    "convert_json_version",
    "import_annotation",
    "export_annotation",
    "convert_project_type",
    "filter_images_by_comments",
    "filter_images_by_tags",
    "filter_annotation_instances",
    # helpers
    "add_annotation_bbox_to_json",
    "add_annotation_comment_to_json",
    "add_annotation_cuboid_to_json",
    "add_annotation_ellipse_to_json",
    "add_annotation_point_to_json",
    "add_annotation_polygon_to_json",
    "add_annotation_polyline_to_json",
    "add_annotation_template_to_json",
    # Teams Section
    "get_team_metadata",
    "invite_contributor_to_team",
    "delete_contributor_to_team_invitation",
    "search_team_contributors",
    # Projects Section
    "create_project_from_metadata",
    "get_project_settings",
    "set_project_settings",
    "get_project_metadata",
    "get_project_workflow",
    "set_project_workflow",
    "search_projects",
    "create_project",
    "clone_project",
    "unshare_project",
    "share_project",
    "delete_project",
    # Images Section
    "search_images",
    "copy_image",
    # Folders Section
    "create_folder",
    "get_folder_metadata",
    "delete_folders",
    "get_project_and_folder_metadata",
    "rename_folder",
    "search_folders",
    "assign_folder",
    "unassign_folder",
    # Image Section
    "copy_images",
    "move_images",
    "move_image",
    "delete_images",
    "download_image",
    "create_fuse_image",
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
    "upload_images_from_public_urls_to_project",
    "upload_images_from_s3_bucket_to_project",
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
    "add_annotation_polyline_to_image",
    "add_annotation_polygon_to_image",
    "add_annotation_point_to_image",
    "add_annotation_ellipse_to_image",
    "add_annotation_template_to_image",
    "add_annotation_cuboid_to_image",
    "add_annotation_comment_to_image",
    "get_image_annotations",
    "search_annotation_classes",
    "create_annotation_classes_from_classes_json",
    "upload_annotations_from_folder_to_project",
    "upload_preannotations_from_folder_to_project",
    "download_annotation_classes_json",
    "download_image_preannotations",
    "set_project_default_image_quality_in_editor",
    "run_prediction",
    "run_segmentation",
    "search_models",
    "download_model",
    "rename_project",
    "run_training",
    "get_project_default_image_quality_in_editor",
    "get_image_bytes",
    "set_image_annotation_status",
    "get_image_preannotations",
    "delete_image",
    "get_annotation_class_metadata",
    "delete_model",
    "benchmark",
    "consensus",
    "plot_model_metrics",
    "upload_video_to_project",
    "stop_model_training",
    "upload_images_to_project",
]

__author__ = "Superannotate"

WORKING_DIR = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(WORKING_DIR)
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logging.config.fileConfig(
    os.path.join(WORKING_DIR, "logging.conf"), disable_existing_loggers=False
)
