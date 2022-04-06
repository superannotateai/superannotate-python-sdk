import os
from pathlib import Path

import lib.core as constances
from lib.app.helpers import extract_project_folder
from lib.core.entities import IntegrationEntity
from lib.core.enums import ProjectType
from lib.infrastructure.controller import Controller


def get_project_name(project):
    project_name = ""
    if isinstance(project, dict):
        project_name = project["name"]
    if isinstance(project, str):
        if "/" in project:
            project_name = project.split("/")[0]
        else:
            project_name = project
    return project_name


def get_team_metadata(**kwargs):
    return {"event_name": "get_team_metadata", "properties": {}}


def invite_contributors_to_team(**kwargs):
    admin = kwargs.get("admin")
    if not admin:
        admin_value = False
    else:
        admin_value = admin
    return {
        "event_name": "invite_contributors_to_team",
        "properties": {"Admin": admin_value},
    }


def search_team_contributors(**kwargs):
    return {
        "event_name": "search_team_contributors",
        "properties": {
            "Email": bool(kwargs.get("email")),
            "Name": bool(kwargs.get("first_name")),
            "Surname": bool(kwargs.get("last_name")),
        },
    }


def search_projects(**kwargs):
    project = kwargs.get("name")
    return {
        "event_name": "search_projects",
        "properties": {
            "Metadata": bool(kwargs.get("return_metadata")),
            "project_name": get_project_name(project[0]) if project else None,
        },
    }


def create_project(**kwargs):
    project = kwargs["project_name"]
    project_type = kwargs["project_type"]
    return {
        "event_name": "create_project",
        "properties": {
            "Project Type": project_type,
            "project_name": get_project_name(project),
        },
    }


def create_project_from_metadata(**kwargs):
    project = kwargs.get("project_metadata")

    return {
        "event_name": "create_project_from_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def clone_project(**kwargs):
    project = kwargs.get("project_name")

    project_metadata = Controller.get_default().get_project_metadata(project).data["project"]
    project_type = ProjectType.get_name(project_metadata.project_type)

    return {
        "event_name": "clone_project",
        "properties": {
            "External": bool(
                project_metadata.upload_state == constances.UploadState.EXTERNAL.value
            ),
            "Project Type": project_type,
            "Copy Classes": bool(kwargs.get("copy_annotation_classes")
                                 ),
            "Copy Settings": bool(kwargs.get("copy_settings")),
            "Copy Workflow": bool(kwargs.get("copy_workflow")),
            "Copy Contributors": bool(kwargs.get("copy_contributors")
                                      ),
            "project_name": get_project_name(project),
        },
    }


def search_images(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "search_images",
        "properties": {
            "Annotation Status": bool(kwargs.get("annotation_status")
                                      ),
            "Metadata": bool(kwargs.get("return_metadata")),
            "project_name": get_project_name(project),
        },
    }


def upload_images_to_project(**kwargs):
    project = kwargs["project"]

    img_paths = kwargs.get("img_paths")
    return {
        "event_name": "upload_images_to_project",
        "properties": {
            "Image Count": len(img_paths) if img_paths else None,
            "Annotation Status": bool(kwargs.get("annotation_status")),
            "From S3": bool(kwargs.get("from_s3")),
            "project_name": get_project_name(project),
        },
    }


def upload_image_to_project(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "upload_image_to_project",
        "properties": {
            "Image Name": bool(kwargs.get("image_name")),
            "Annotation Status": bool(kwargs.get("annotation_status")
                                      ),
            "project_name": get_project_name(project),
        },
    }


def upload_video_to_project(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "upload_video_to_project",
        "properties": {
            "project_name": get_project_name(project),
            "FPS": bool(kwargs.get("target_fps")),
            "Start": bool(kwargs.get("start_time")),
            "End": bool(kwargs.get("end_time")),
        },
    }


def attach_image_urls_to_project(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "attach_image_urls_to_project",
        "properties": {
            "project_name": get_project_name(project),
            "Annotation Status": bool(kwargs.get("annotation_status")
                                      ),
        },
    }


def set_images_annotation_statuses(**kwargs):
    project = kwargs["project"]
    annotation_status = kwargs.get("annotation_status")
    image_names = kwargs["image_names"]
    return {
        "event_name": "set_images_annotation_statuses",
        "properties": {
            "project_name": get_project_name(project),
            "Image Count": len(image_names) if image_names else None,
            "Annotation Status": annotation_status,
        },
    }


def download_image_annotations(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "download_image_annotations",
        "properties": {"project_name": get_project_name(project)},
    }


def get_image_metadata(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "get_image_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def add_annotation_comment_to_image(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "add_annotation_comment_to_image",
        "properties": {"project_name": get_project_name(project)},
    }


def delete_annotation_class(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "delete_annotation_class",
        "properties": {"project_name": get_project_name(project)},
    }


def download_annotation_classes_json(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "download_annotation_classes_json",
        "properties": {"project_name": get_project_name(project)},
    }


def search_annotation_classes(**kwargs):
    project = kwargs["project"]
    name_prefix = kwargs.get("name_prefix")

    return {
        "event_name": "search_annotation_classes",
        "properties": {
            "project_name": get_project_name(project),
            "Prefix": bool(name_prefix),
        },
    }


def get_project_image_count(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "get_project_image_count",
        "properties": {"project_name": get_project_name(project)},
    }


def get_project_settings(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "get_project_settings",
        "properties": {"project_name": get_project_name(project)},
    }


def get_project_metadata(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "get_project_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def delete_project(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "delete_project",
        "properties": {"project_name": get_project_name(project)},
    }


def rename_project(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "rename_project",
        "properties": {"project_name": get_project_name(project)},
    }


def get_project_workflow(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "get_project_workflow",
        "properties": {"project_name": get_project_name(project)},
    }


def set_project_workflow(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "set_project_workflow",
        "properties": {"project_name": get_project_name(project)},
    }


def create_folder(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "create_folder",
        "properties": {"project_name": get_project_name(project)},
    }


def get_folder_metadata(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "get_folder_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def get_project_and_folder_metadata(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "get_project_and_folder_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def search_images_all_folders(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "search_images_all_folders",
        "properties": {
            "Annotation Status": bool(kwargs.get("annotation_status")
                                      ),
            "Metadata": bool(kwargs.get("return_metadata")),
            "project_name": get_project_name(project),
        },
    }


def download_model(**kwargs):
    model = kwargs["model"]
    return {
        "event_name": "download_model",
        "properties": {"model": model},
    }


def convert_project_type(**kwargs):
    return {
        "event_name": "convert_project_type",
        "properties": {},
    }


def convert_json_version(**kwargs):
    return {
        "event_name": "convert_json_version",
        "properties": {},
    }


def upload_image_annotations(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "upload_image_annotations",
        "properties": {
            "project_name": get_project_name(project),
            "Pixel": bool("mask" in kwargs),
        },
    }


def download_image(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "download_image",
        "properties": {
            "project_name": get_project_name(project),
            "Download Annotations": bool("include_annotations" in kwargs),
            "Download Fuse": bool("include_fuse" in kwargs),
            "Download Overlay": bool("include_overlay" in kwargs),
        },
    }


def copy_image(**kwargs):
    project = kwargs["source_project"]
    return {
        "event_name": "copy_image",
        "properties": {
            "project_name": get_project_name(project),
            "Copy Annotations": bool("include_annotations" in kwargs),
            "Copy Annotation Status": bool("copy_annotation_status" in kwargs),
            "Copy Pin": bool("copy_pin" in kwargs),
        },
    }


def run_prediction(**kwargs):
    project = kwargs["project"]
    project_name = get_project_name(project)
    res = Controller.get_default().get_project_metadata(project_name)
    project_metadata = res.data["project"]
    project_type = ProjectType.get_name(project_metadata.project_type)
    image_list = kwargs["images_list"]
    return {
        "event_name": "run_prediction",
        "properties": {
            "Project Type": project_type,
            "Image Count": len(image_list) if image_list else None
        },
    }


def upload_videos_from_folder_to_project(**kwargs):
    folder_path = kwargs["folder_path"]
    glob_iterator = Path(folder_path).glob("*")
    return {
        "event_name": "upload_videos_from_folder_to_project",
        "properties": {"Video Count": sum(1 for _ in glob_iterator)},
    }


def export_annotation(**kwargs):
    dataset_format = kwargs["dataset_format"]
    project_type = kwargs["project_type"]
    if not project_type:
        project_type = "Vector"

    task = kwargs.get("task")
    if not task:
        task = "object_detection"
    return {
        "event_name": "export_annotation",
        "properties": {
            "Format": dataset_format,
            "Project Type": project_type,
            "Task": task,
        },
    }


def import_annotation(**kwargs):
    dataset_format = kwargs["dataset_format"]
    project_type = kwargs["project_type"]
    if not project_type:
        project_type = "Vector"
    task = kwargs.get("task")
    if not task:
        task = "object_detection"
    return {
        "event_name": "import_annotation",
        "properties": {
            "Format": dataset_format,
            "Project Type": project_type,
            "Task": task,
        },
    }


def move_images(**kwargs):
    project = kwargs["source_project"]
    project_name, folder_name = extract_project_folder(project)
    image_names = kwargs.get("image_names", False)
    if image_names is None:
        res = Controller.get_default().search_images(project_name, folder_name)
        image_names = res.data

    return {
        "event_name": "move_images",
        "properties": {
            "project_name": project_name,
            "Image Count": len(image_names),
            "Copy Annotations": bool("include_annotations" in kwargs),
            "Copy Annotation Status": bool("copy_annotation_status" in kwargs),
            "Copy Pin": bool("copy_pin" in kwargs),
        },
    }


def copy_images(**kwargs):
    project = kwargs["source_project"]
    project_name, folder_name = extract_project_folder(project)
    image_names = kwargs.get("image_names", False)
    if not image_names:
        res = Controller.get_default().search_images(project_name, folder_name)
        image_names = res.data
    return {
        "event_name": "copy_images",
        "properties": {
            "project_name": project_name,
            "Image Count": len(image_names),
            "Copy Annotations": bool("include_annotations" in kwargs),
            "Copy Annotation Status": bool("copy_annotation_status" in kwargs),
        },
    }


def consensus(**kwargs):
    folder_names = kwargs["folder_names"]
    image_list = kwargs["image_list"]
    annot_type = kwargs.get("annot_type")
    if not annot_type:
        annot_type = "bbox"
    show_plots = kwargs.get("show_plots")
    if not show_plots:
        show_plots = False
    return {
        "event_name": "consensus",
        "properties": {
            "Folder Count": len(folder_names),
            "Image Count": len(image_list) if image_list else None,
            "Annotation Type": annot_type,
            "Plot": show_plots,
        },
    }


def benchmark(**kwargs):
    folder_names = kwargs.get("folder_names")
    image_list = kwargs.get("image_list")
    annot_type = kwargs.get("annot_type")
    if not annot_type:
        annot_type = "bbox"
    show_plots = kwargs.get("show_plots")
    if not show_plots:
        show_plots = False

    return {
        "event_name": "benchmark",
        "properties": {
            "Folder Count": len(folder_names) if folder_names else None,
            "Image Count": len(image_list) if image_list else None,
            "Annotation Type": annot_type,
            "Plot": show_plots,
        },
    }


def upload_annotations_from_folder_to_project(**kwargs):
    project = kwargs["project"]
    project_name = get_project_name(project)
    res = Controller.get_default().get_project_metadata(project_name)
    project_metadata = res.data["project"]
    project_type = ProjectType.get_name(project_metadata.project_type)

    folder_path = kwargs["folder_path"]
    glob_iterator = Path(folder_path).glob("*.json")
    return {
        "event_name": "upload_annotations_from_folder_to_project",
        "properties": {
            "Annotation Count": sum(1 for _ in glob_iterator),
            "Project Type": project_type,
            "From S3": bool("from_s3_bucket" in kwargs),
        },
    }


def upload_preannotations_from_folder_to_project(**kwargs):
    project = kwargs["project"]

    project_name = get_project_name(project)
    res = Controller.get_default().get_project_metadata(project_name)
    project_metadata = res.data["project"]
    project_type = ProjectType.get_name(project_metadata.project_type)
    folder_path = kwargs["folder_path"]
    glob_iterator = Path(folder_path).glob("*.json")
    return {
        "event_name": "upload_preannotations_from_folder_to_project",
        "properties": {
            "Annotation Count": sum(1 for _ in glob_iterator),
            "Project Type": project_type,
            "From S3": bool("from_s3_bucket" in kwargs),
        },
    }


def upload_images_from_folder_to_project(**kwargs):
    folder_path = kwargs["folder_path"]
    recursive_subfolders = kwargs["recursive_subfolders"]
    extensions = kwargs["extensions"]
    if not extensions:
        extensions = constances.DEFAULT_IMAGE_EXTENSIONS
    exclude_file_patterns = kwargs["exclude_file_patterns"]
    if not exclude_file_patterns:
        exclude_file_patterns = constances.DEFAULT_FILE_EXCLUDE_PATTERNS

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
        not_in_exclude_list = [x not in Path(path).name for x in exclude_file_patterns]
        if all(not_in_exclude_list):
            filtered_paths.append(path)

    return {
        "event_name": "upload_images_from_folder_to_project",
        "properties": {
            "Image Count": len(filtered_paths),
            "Custom Extentions": bool(kwargs["extensions"]),
            "Annotation Status": bool(kwargs.get("annotation_status")
                                      ),
            "From S3": bool(kwargs.get("from_s3_bucket")),
            "Custom Exclude Patters": bool(kwargs["exclude_file_patterns"]),
        },
    }


def prepare_export(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "prepare_export",
        "properties": {
            "project_name": get_project_name(project),
            "Folder Count": bool(kwargs.get("folder_names")),
            "Annotation Statuses": bool(kwargs.get("annotation_statuses")
                                        ),
            "Include Fuse": bool(kwargs.get("include_fuse")),
            "Only Pinned": bool(kwargs.get("only_pinned")),
        },
    }


def download_export(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "download_export",
        "properties": {
            "project_name": get_project_name(project),
            "to_s3_bucket": bool(kwargs.get("to_s3_bucket")),
        },
    }


def assign_images(**kwargs):
    project = kwargs["project"]
    project_name, folder_name = extract_project_folder(project)
    image_names = kwargs.get("image_names")
    user = kwargs.get("user")

    contributors = (
        Controller.get_default().get_project_metadata(project_name=project_name, include_contributors=True)
            .data["contributors"]
    )
    contributor = None
    for c in contributors:
        if c["user_id"] == user:
            contributor = c
    user_role = "ADMIN"
    if contributor["user_role"] == 3:
        user_role = "ANNOTATOR"
    if contributor["user_role"] == 4:
        user_role = "QA"
    is_root = True
    if folder_name:
        is_root = False

    return {
        "event_name": "assign_images",
        "properties": {
            "project_name": project_name,
            "Assign Folder": is_root,
            "Image Count": len(image_names) if image_names else None,
            "User Role": user_role,
        },
    }


def pin_image(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "pin_image",
        "properties": {
            "project_name": get_project_name(project),
            "Pin": bool("pin" in kwargs),
        },
    }


def set_image_annotation_status(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "set_image_annotation_status",
        "properties": {
            "project_name": get_project_name(project),
            "Annotation Status": bool("annotation_status" in kwargs),
        },
    }


def add_annotation_bbox_to_image(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "add_annotation_bbox_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool("annotation_class_attributes" in kwargs),
            "Error": bool("error" in kwargs),
        },
    }


def add_annotation_point_to_image(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "add_annotation_point_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool("annotation_class_attributes" in kwargs),
            "Error": bool("error" in kwargs),
        },
    }


def create_annotation_class(**kwargs):
    project = kwargs["project"]
    class_type = kwargs.get("class_type")

    return {
        "event_name": "create_annotation_class",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool("attribute_groups" in kwargs),
            "class_type": class_type if class_type else "object",
        },
    }


def create_annotation_classes_from_classes_json(**kwargs):
    project = kwargs["project"]
    return {
        "event_name": "create_annotation_classes_from_classes_json",
        "properties": {
            "project_name": get_project_name(project),
            "From S3": bool("from_s3_bucket" in kwargs),
        },
    }


def class_distribution(**kwargs):
    return {
        "event_name": "class_distribution",
        "properties": {"Plot": bool("visualize" in kwargs)},
    }


def share_project(**kwargs):
    project = kwargs["project_name"]

    user_role = kwargs.get("user_role")
    return {
        "event_name": "share_project",
        "properties": {
            "project_name": get_project_name(project),
            "User Role": user_role,
        },
    }


def set_project_default_image_quality_in_editor(**kwargs):
    project = kwargs["project"]

    image_quality_in_editor = kwargs.get("image_quality_in_editor")
    return {
        "event_name": "set_project_default_image_quality_in_editor",
        "properties": {
            "project_name": get_project_name(project),
            "Image Quality": image_quality_in_editor,
        },
    }


def get_exports(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "get_exports",
        "properties": {
            "project_name": get_project_name(project),
            "Metadata": bool("return_metadata" in kwargs),
        },
    }


def search_folders(**kwargs):
    project = kwargs["project"]

    return {
        "event_name": "search_folders",
        "properties": {
            "project_name": get_project_name(project),
            "Metadata": bool("return_metadata" in kwargs),
        },
    }


def aggregate_annotations_as_df(**kwargs):
    folder_names = kwargs.get("folder_names")
    if not folder_names:
        folder_names = []

    project_type = kwargs["project_type"]

    return {
        "event_name": "aggregate_annotations_as_df",
        "properties": {"Folder Count": len(folder_names), "Project Type": project_type},
    }


def delete_folders(**kwargs):
    project = kwargs["project"]
    folder_names = kwargs.get("folder_names")
    if not folder_names:
        folder_names = []
    return {
        "event_name": "delete_folders",
        "properties": {
            "project_name": get_project_name(project),
            "Folder Count": len(folder_names),
        },
    }


def delete_images(**kwargs):
    project = kwargs["project"]
    project_name, folder_name = extract_project_folder(project)

    image_names = kwargs.get("image_names", False)
    if not image_names:
        res = Controller.get_default().search_images(project_name, folder_name)
        image_names = res.data
    return {
        "event_name": "delete_images",
        "properties": {
            "project_name": project_name,
            "Image Count": len(image_names),
        },
    }


def unassign_folder(**kwargs):
    return {"event_name": "unassign_folder", "properties": {}}


def assign_folder(**kwargs):
    users = kwargs.get("users")
    return {"event_name": "assign_folder", "properties": {"User Count": len(users)}}


def unassign_images(**kwargs):
    image_names = kwargs.get("image_names")

    project = kwargs["project"]

    _, folder_name = extract_project_folder(project)
    is_root = True
    if folder_name:
        is_root = False

    return {
        "event_name": "unassign_images",
        "properties": {"Assign Folder": is_root, "Image Count": len(image_names)},
    }


def attach_video_urls_to_project(**kwargs):
    project = kwargs["project"]
    project_name, _ = extract_project_folder(project)
    return {
        "event_name": "attach_video_urls_to_project",
        "properties": {
            "project_name": project_name,
            "Annotation Status": bool(kwargs.get("annotation_status")),
        },
    }


def attach_document_urls_to_project(**kwargs):
    project = kwargs["project"]
    project_name, _ = extract_project_folder(project)
    return {
        "event_name": "attach_document_urls_to_project",
        "properties": {
            "project_name": project_name,
            "Annotation Status": bool(kwargs.get("annotation_status")),
        },
    }


def delete_annotations(**kwargs):
    return {"event_name": "delete_annotations", "properties": {}}


def validate_annotations(**kwargs):
    project_type = kwargs["project_type"]
    return {
        "event_name": "validate_annotations",
        "properties": {"Project Type": project_type},
    }


def add_contributors_to_project(**kwargs):
    user_role = kwargs.get("role")

    return {
        "event_name": "add_contributors_to_project",
        "properties": {"User Role": user_role},
    }


def get_annotations(**kwargs):
    project = kwargs["project"]
    items = kwargs["items"]

    return {
        "event_name": "get_annotations",
        "properties": {"Project": project, "items_count": len(items) if items else None},
    }


def get_annotations_per_frame(**kwargs):
    project = kwargs["project"]
    fps = kwargs["fps"]
    if not fps:
        fps = 1
    return {
        "event_name": "get_annotations_per_frame",
        "properties": {"Project": project, "fps": fps},
    }


def upload_priority_scores(**kwargs):
    scores = kwargs["scores"]
    return {
        "event_name": "upload_priority_scores",
        "properties": {"Score Count": len(scores) if scores else None},
    }


def get_integrations(**kwargs):
    return {
        "event_name": "get_integrations",
        "properties": {},
    }


def attach_items_from_integrated_storage(**kwargs):
    project = kwargs.get("project")
    project_name, _ = extract_project_folder(project)
    integration = kwargs.get("integration")
    folder_path = kwargs.get("folder_path")

    if isinstance(integration, str):
        integration = IntegrationEntity(name=integration)
    project = Controller.get_default().get_project_metadata(project_name).data["project"]
    return {
        "event_name": "attach_items_from_integrated_storage",
        "properties": {
            "project_type": ProjectType.get_name(project.project_type),
            "integration_name": integration.name,
            "folder_path": bool(folder_path),
        },
    }


def query(**kwargs):
    project = kwargs["project"]
    query_str = kwargs["query"]
    project_name, folder_name = extract_project_folder(project)
    project = Controller.get_default().get_project_metadata(project_name).data["project"]
    return {
        "event_name": "query_saqul",
        "properties": {
            "project_type": ProjectType.get_name(project.project_type),
            "query": query_str,
        },
    }


def get_item_metadata(**kwargs):
    project = kwargs["project"]
    project_name, _ = extract_project_folder(project)
    project = Controller.get_default().get_project_metadata(project_name).data["project"]
    return {
        "event_name": "get_item_metadata",
        "properties": {"project_type": ProjectType.get_name(project.project_type)},
    }


def search_items(**kwargs):
    project = kwargs["project"]
    name_contains = kwargs["name_contains"]
    annotation_status = kwargs["annotation_status"]
    annotator_email = kwargs["annotator_email"]
    qa_email = kwargs["qa_email"]
    recursive = kwargs["recursive"]
    project_name, folder_name = extract_project_folder(project)
    project = Controller.get_default().get_project_metadata(project_name).data["project"]
    return {
        "event_name": "search_items",
        "properties": {
            "project_type": ProjectType.get_name(project.project_type),
            "query": query,
            "name_contains": len(name_contains) if name_contains else False,
            "annotation_status": annotation_status if annotation_status else False,
            "annotator_email": bool(annotator_email),
            "qa_email": bool(qa_email),
            "recursive": bool(recursive),
        },
    }
