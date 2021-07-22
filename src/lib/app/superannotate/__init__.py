from src.lib.app.analytics.class_analytics import aggregate_annotations_as_df
from src.lib.app.analytics.class_analytics import attribute_distribution
from src.lib.app.analytics.class_analytics import class_distribution
from src.lib.app.annotation_helpers import add_annotation_bbox_to_json
from src.lib.app.annotation_helpers import add_annotation_comment_to_json
from src.lib.app.annotation_helpers import add_annotation_cuboid_to_json
from src.lib.app.annotation_helpers import add_annotation_ellipse_to_json
from src.lib.app.annotation_helpers import add_annotation_point_to_json
from src.lib.app.annotation_helpers import add_annotation_polygon_to_json
from src.lib.app.annotation_helpers import add_annotation_polyline_to_json
from src.lib.app.annotation_helpers import add_annotation_template_to_json
from src.lib.app.convertors.df_converter import df_to_annotations
from src.lib.app.convertors.df_converter import filter_annotation_instances
from src.lib.app.convertors.df_converter import filter_images_by_comments
from src.lib.app.convertors.df_converter import filter_images_by_tags
from src.lib.app.convertors.dicom_converter import dicom_to_rgb_sequence
from src.lib.app.input_converters.conversion import coco_split_dataset
from src.lib.app.input_converters.conversion import convert_json_version
from src.lib.app.input_converters.conversion import convert_project_type
from src.lib.app.input_converters.conversion import export_annotation
from src.lib.app.input_converters.conversion import import_annotation
from src.lib.app.interface.sdk_interface import assign_folder
from src.lib.app.interface.sdk_interface import assign_images
from src.lib.app.interface.sdk_interface import clone_project
from src.lib.app.interface.sdk_interface import copy_image
from src.lib.app.interface.sdk_interface import copy_images
from src.lib.app.interface.sdk_interface import create_annotation_class
from src.lib.app.interface.sdk_interface import (
    create_annotation_classes_from_classes_json,
)
from src.lib.app.interface.sdk_interface import create_folder
from src.lib.app.interface.sdk_interface import create_project
from src.lib.app.interface.sdk_interface import delete_contributor_to_team_invitation
from src.lib.app.interface.sdk_interface import delete_folders
from src.lib.app.interface.sdk_interface import delete_images
from src.lib.app.interface.sdk_interface import delete_project
from src.lib.app.interface.sdk_interface import get_folder_metadata
from src.lib.app.interface.sdk_interface import get_project_and_folder_metadata
from src.lib.app.interface.sdk_interface import get_team_metadata
from src.lib.app.interface.sdk_interface import invite_contributor_to_team
from src.lib.app.interface.sdk_interface import move_images
from src.lib.app.interface.sdk_interface import rename_folder
from src.lib.app.interface.sdk_interface import search_annotation_classes
from src.lib.app.interface.sdk_interface import search_folders
from src.lib.app.interface.sdk_interface import search_images
from src.lib.app.interface.sdk_interface import search_projects
from src.lib.app.interface.sdk_interface import search_team_contributors
from src.lib.app.interface.sdk_interface import share_project
from src.lib.app.interface.sdk_interface import unassign_folder
from src.lib.app.interface.sdk_interface import unassign_images
from src.lib.app.interface.sdk_interface import (
    upload_images_from_google_cloud_to_project,
)
from src.lib.app.interface.sdk_interface import upload_images_from_s3_bucket_to_project
from src.lib.app.interface.sdk_interface import upload_videos_from_folder_to_project

# todo is it correct df_to_annotations ?
# from src.lib.app.analytics.common import df_to_annotations


__author__ = "Superannotate"
__version__ = ""
__all__ = [
    # analytics
    "attribute_distribution",
    "class_distribution",
    "aggregate_annotations_as_df",
    # common
    "df_to_annotations",
    # convertors
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
    # My Teams Section
    "get_team_metadata",
    "invite_contributor_to_team",
    "delete_contributor_to_team_invitation",
    "search_team_contributors",
    # Teams Section
    "get_team_metadata",
    "invite_contributor_to_team",
    "delete_contributor_to_team_invitation",
    "search_team_contributors",
    # Projects Section
    "search_projects",
    "create_project",
    "clone_project",
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
    "delete_images",
    "assign_images",
    "unassign_images",
    "upload_images_from_google_cloud_to_project",
    "upload_images_from_s3_bucket_to_project",
    # Video Section
    "upload_videos_from_folder_to_project",
    # Annotation Section
    "create_annotation_class",
    "search_annotation_classes",
    "create_annotation_classes_from_classes_json",
]
