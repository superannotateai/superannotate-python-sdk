import lib.core as constances
from lib.app.helpers import extract_project_folder
from lib.core.enums import ProjectType
from lib.infrastructure.controller import Controller

controller = Controller.get_instance()


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


def get_team_metadata(*args, **kwargs):
    return {"event_name": "get_team_metadata", "properties": {}}


def invite_contributor_to_team(*args, **kwargs):
    admin = kwargs.get("admin", None)
    if not admin:
        admin = args[1:2]
    if admin:
        admin = "CUSTOM"
    else:
        admin = "DEFAULT"
    return {"event_name": "invite_contributor_to_team", "properties": {"Admin": admin}}


def search_team_contributors(*args, **kwargs):
    return {
        "event_name": "search_team_contributors",
        "properties": {
            "Email": bool(args[0:1] or kwargs.get("email", None)),
            "Name": bool(args[1:2] or kwargs.get("first_name", None)),
            "Surname": bool(args[2:3] or kwargs.get("last_name", None)),
        },
    }


def search_projects(*args, **kwargs):
    project = kwargs.get("name", None)
    if not project:
        project_name = None
        project = args[0:1]
        if project:
            project_name = get_project_name(project[0])
    else:
        project_name = get_project_name(project)
    return {
        "event_name": "search_projects",
        "properties": {
            "Metadata": bool(args[2:3] or kwargs.get("return_metadata", None)),
            "project_name": project_name,
        },
    }


def create_project(*args, **kwargs):
    project = kwargs.get("project_name", None)
    if not project:
        project = args[0]
    project_type = kwargs.get("project_type", None)
    if not project_type:
        project_type = args[2]
    return {
        "event_name": "create_project",
        "properties": {
            "Project Type": project_type,
            "project_name": get_project_name(project),
        },
    }


def create_project_from_metadata(*args, **kwargs):
    project = kwargs.get("project_metadata", None)
    if not project:
        project = args[0]
    return {
        "event_name": "create_project_from_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def clone_project(*args, **kwargs):
    project = kwargs.get("project_name", None)
    if not project:
        project = args[0]

    result = controller.get_project_metadata(project)
    project_metadata = result.data["project"]
    project_type = ProjectType.get_name(project_metadata.project_type)

    return {
        "event_name": "clone_project",
        "properties": {
            "External": bool(
                project_metadata.upload_state == constances.UploadState.EXTERNAL.value
            ),
            "Project Type": project_type,
            "Copy Classes": bool(
                args[3:4] or kwargs.get("copy_annotation_classes", None)
            ),
            "Copy Settings": bool(args[4:5] or kwargs.get("copy_settings", None)),
            "Copy Workflow": bool(args[5:6] or kwargs.get("copy_workflow", None)),
            "Copy Contributors": bool(
                args[6:7] or kwargs.get("copy_contributors", None)
            ),
            "project_name": get_project_name(project),
        },
    }


def search_images(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "search_images",
        "properties": {
            "Annotation Status": bool(
                args[2:3] or kwargs.get("annotation_status", None)
            ),
            "Metadata": bool(args[3:4] or kwargs.get("return_metadata", None)),
            "project_name": get_project_name(project),
        },
    }


def upload_images_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    img_paths = kwargs.get("img_paths", [])
    if not img_paths:
        img_paths += args[1]
    return {
        "event_name": "upload_images_to_project",
        "properties": {
            "Image Count": len(img_paths),
            "Annotation Status": bool(
                args[2:3] or kwargs.get("annotation_status", None)
            ),
            "From S3": bool(args[3:4] or kwargs.get("from_s3", None)),
            "project_name": get_project_name(project),
        },
    }


def upload_image_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "upload_image_to_project",
        "properties": {
            "Image Name": bool(args[2:3] or kwargs.get("image_name", None)),
            "Annotation Status": bool(
                args[3:4] or kwargs.get("annotation_status", None)
            ),
            "project_name": get_project_name(project),
        },
    }


def upload_images_from_public_urls_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    img_urls = kwargs.get("img_urls", [])
    if not img_urls:
        img_urls += args[1]
    return {
        "event_name": "upload_images_from_public_urls_to_project",
        "properties": {
            "Image Count": len(img_urls),
            "Image Name": bool(args[2:3] or kwargs.get("img_names", None)),
            "Annotation Status": bool(
                args[3:4] or kwargs.get("annotation_status", None)
            ),
            "project_name": get_project_name(project),
        },
    }


def upload_video_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]

    return {
        "event_name": "upload_video_to_project",
        "properties": {
            "project_name": get_project_name(project),
            "FPS": bool(args[2:3] or kwargs.get("target_fps", None)),
            "Start": bool(args[3:4] or kwargs.get("start_time", None)),
            "End": bool(args[4:5] or kwargs.get("end_time", None)),
        },
    }


def attach_image_urls_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "attach_image_urls_to_project",
        "properties": {
            "project_name": get_project_name(project),
            "Annotation Status": bool(
                args[2:3] or kwargs.get("annotation_status", None)
            ),
        },
    }


def set_images_annotation_statuses(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    annotation_status = kwargs.get("annotation_status", None)
    if not annotation_status:
        annotation_status = args[2]
    image_names = kwargs.get("image_names", [])
    if not image_names:
        image_names = args[1]
    return {
        "event_name": "set_images_annotation_statuses",
        "properties": {
            "project_name": get_project_name(project),
            "Image Count": len(image_names),
            "Annotation Status": annotation_status,
        },
    }


def get_image_annotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "get_image_annotations",
        "properties": {"project_name": get_project_name(project)},
    }


def download_image_annotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "download_image_annotations",
        "properties": {"project_name": get_project_name(project)},
    }


def get_image_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "get_image_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def add_annotation_comment_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "add_annotation_comment_to_image",
        "properties": {"project_name": get_project_name(project)},
    }


def delete_annotation_class(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "delete_annotation_class",
        "properties": {"project_name": get_project_name(project)},
    }


def download_annotation_classes_json(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "download_annotation_classes_json",
        "properties": {"project_name": get_project_name(project)},
    }


def search_annotation_classes(*args, **kwargs):
    project = kwargs.get("project", None)
    name_prefix = kwargs.get("name_prefix", None)
    if not name_prefix:
        name_prefix = args[1:2]
        if not name_prefix:
            name_prefix = None
    if not project:
        project = args[0]
    return {
        "event_name": "search_annotation_classes",
        "properties": {
            "project_name": get_project_name(project),
            "Prefix": bool(name_prefix),
        },
    }


def get_project_image_count(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "get_project_image_count",
        "properties": {"project_name": get_project_name(project)},
    }


def get_project_settings(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "get_project_settings",
        "properties": {"project_name": get_project_name(project)},
    }


def get_project_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "get_project_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def delete_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "delete_project",
        "properties": {"project_name": get_project_name(project)},
    }


def rename_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "rename_project",
        "properties": {"project_name": get_project_name(project)},
    }


def get_project_workflow(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]

    return {
        "event_name": "get_project_workflow",
        "properties": {"project_name": get_project_name(project)},
    }


def set_project_workflow(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "set_project_workflow",
        "properties": {"project_name": get_project_name(project)},
    }


def create_folder(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "create_folder",
        "properties": {"project_name": get_project_name(project)},
    }


def get_folder_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "get_folder_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def get_project_and_folder_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "get_project_and_folder_metadata",
        "properties": {"project_name": get_project_name(project)},
    }


def search_images_all_folders(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "search_images_all_folders",
        "properties": {
            "Annotation Status": bool(
                args[2:3] or kwargs.get("annotation_status", None)
            ),
            "Metadata": bool(args[3:4] or kwargs.get("return_metadata", None)),
            "project_name": get_project_name(project),
        },
    }


def download_model(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "download_model",
        "properties": {"project_name": get_project_name(project)},
    }


def convert_project_type(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "convert_project_type",
        "properties": {"project_name": get_project_name(project)},
    }


def convert_json_version(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "convert_json_version",
        "properties": {"project_name": get_project_name(project)},
    }


def upload_image_annotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "upload_image_annotations",
        "properties": {
            "project_name": get_project_name(project),
            "Pixel": bool(args[3:4] or ("mask" in kwargs)),
        },
    }


def download_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "download_image",
        "properties": {
            "project_name": get_project_name(project),
            "Download Annotations": bool(
                args[3:4] or ("include_annotations" in kwargs)
            ),
            "Download Fuse": bool(args[4:5] or ("include_fuse" in kwargs)),
            "Download Overlay": bool(args[5:6] or ("include_overlay" in kwargs)),
        },
    }


def copy_image(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "copy_image",
        "properties": {
            "project_name": get_project_name(project),
            "Copy Annotations": bool(args[3:4] or ("include_annotations" in kwargs)),
            "Copy Annotation Status": bool(
                args[4:5] or ("copy_annotation_status" in kwargs)
            ),
            "Copy Pin": bool(args[5:6] or ("copy_pin" in kwargs)),
        },
    }


def run_prediction(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    project_name = get_project_name(project)
    res = controller.get_project_metadata(project_name)
    project_metadata = res.data["project"]
    project_type = ProjectType.get_name(project_metadata.project_type)
    image_list = kwargs.get("images_list", None)
    if not image_list:
        image_list = args[1]
    return {
        "event_name": "run_prediction",
        "properties": {"Project Type": project_type, "Image Count": len(image_list)},
    }


def upload_videos_from_folder_to_project(*args, **kwargs):
    folder_path = kwargs.get("folder_path", None)
    if not folder_path:
        folder_path = args[1]
    from pathlib import Path

    glob_iterator = Path(folder_path).glob("*")
    return {
        "event_name": "upload_videos_from_folder_to_project",
        "properties": {"Video Count": sum(1 for _ in glob_iterator)},
    }


def export_annotation(*args, **kwargs):
    dataset_format = kwargs.get("dataset_format", None)
    if not dataset_format:
        dataset_format = args[2]
    project_type = kwargs.get("project_type", None)
    if not project_type:
        project_type = args[4:5]
        if not project_type:
            project_type = "Vector"
        else:
            project_type = args[4]
    task = kwargs.get("task", None)
    if not task:
        task = args[5:6]
        if not task:
            task = "object_detection"
        else:
            task = args[5]
    return {
        "event_name": "export_annotation",
        "properties": {
            "Format": dataset_format,
            "Project Type": project_type,
            "Task": task,
        },
    }


def import_annotation(*args, **kwargs):
    dataset_format = kwargs.get("dataset_format", None)
    if not dataset_format:
        dataset_format = args[2]
    project_type = kwargs.get("project_type", None)
    if not project_type:
        project_type = args[4:5]
        if not project_type:
            project_type = "Vector"
        else:
            project_type = args[4]
    task = kwargs.get("task", None)
    if not task:
        task = args[5:6]
        if not task:
            task = "object_detection"
        else:
            task = args[5]
    return {
        "event_name": "import_annotation",
        "properties": {
            "Format": dataset_format,
            "Project Type": project_type,
            "Task": task,
        },
    }


def move_images(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0]
    image_names = kwargs.get("image_names", False)
    if image_names == False:
        image_names = args[1]
        if image_names is None:
            res = controller.search_images(project)
            image_names = res.data

    return {
        "event_name": "move_images",
        "properties": {
            "project_name": get_project_name(project),
            "Image Count": len(image_names),
            "Copy Annotations": bool(args[3:4] or ("include_annotations" in kwargs)),
            "Copy Annotation Status": bool(
                args[4:5] or ("copy_annotation_status" in kwargs)
            ),
            "Copy Pin": bool(args[5:6] or ("copy_pin" in kwargs)),
        },
    }


def copy_images(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0]
    image_names = kwargs.get("image_names", False)
    if image_names == False:
        image_names = args[1]
        if image_names is None:
            res = controller.search_images(project)
            image_names = res.data
    return {
        "event_name": "copy_images",
        "properties": {
            "project_name": get_project_name(project),
            "Image Count": len(image_names),
            "Copy Annotations": bool(args[3:4] or ("include_annotations" in kwargs)),
            "Copy Annotation Status": bool(
                args[4:5] or ("copy_annotation_status" in kwargs)
            ),
            "Copy Pin": bool(args[5:6] or ("copy_pin" in kwargs)),
        },
    }


def consensus(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0]
    folder_names = kwargs.get("folder_names", None)
    if not folder_names:
        folder_names = args[1]
    image_list = kwargs.get("image_list", "empty")
    if image_list == "empty":
        image_list = args[4:5]
        if image_list:
            if image_list[0] is None:
                res = controller.search_images(project)
                image_list = res.data
            else:
                image_list = image_list[0]
    annot_type = kwargs.get("annot_type", "empty")
    if annot_type == "empty":
        annot_type = args[4:5]
        if not annot_type:
            annot_type = "bbox"
        else:
            annot_type = args[4]

    show_plots = kwargs.get("show_plots", "empty")
    if show_plots == "empty":
        show_plots = args[5:6]
        if not show_plots:
            show_plots = False
        else:
            show_plots = args[5]
    return {
        "event_name": "consensus",
        "properties": {
            "Folder Count": len(folder_names),
            "Image Count": len(image_list),
            "Annotation Type": annot_type,
            "Plot": show_plots,
        },
    }


def benchmark(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0]
    folder_names = kwargs.get("folder_names", None)
    if not folder_names:
        folder_names = args[2]
    image_list = kwargs.get("image_list", "empty")
    if image_list == "empty":
        image_list = args[4:5]
        if image_list:
            if image_list[0] is None:
                res = controller.search_images(project)
                image_list = res.data
            else:
                image_list = image_list[0]
    annot_type = kwargs.get("annot_type", "empty")
    if annot_type == "empty":
        annot_type = args[5:6]
        if not annot_type:
            annot_type = "bbox"
        else:
            annot_type = args[5]

    show_plots = kwargs.get("show_plots", "empty")
    if show_plots == "empty":
        show_plots = args[6:7]
        if not show_plots:
            show_plots = False
        else:
            show_plots = args[6]
    return {
        "event_name": "benchmark",
        "properties": {
            "Folder Count": len(folder_names),
            "Image Count": len(image_list),
            "Annotation Type": annot_type,
            "Plot": show_plots,
        },
    }


def upload_annotations_from_folder_to_project(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0]
    project_name = get_project_name(project)
    res = controller.get_project_metadata(project_name)
    project_metadata = res.data["project"]
    project_type = ProjectType.get_name(project_metadata.project_type)

    folder_path = kwargs.get("folder_path", None)
    if not folder_path:
        folder_path = args[1]
    from pathlib import Path

    glob_iterator = Path(folder_path).glob("*.json")
    return {
        "event_name": "upload_annotations_from_folder_to_project",
        "properties": {
            "Annotation Count": sum(1 for _ in glob_iterator),
            "Project Type": project_type,
            "From S3": bool(args[2:3] or ("from_s3_bucket" in kwargs)),
        },
    }


def upload_preannotations_from_folder_to_project(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0]
    project_name = get_project_name(project)
    res = controller.get_project_metadata(project_name)
    project_metadata = res.data["project"]
    project_type = ProjectType.get_name(project_metadata.project_type)
    folder_path = kwargs.get("folder_path", None)
    if not folder_path:
        folder_path = args[1]
    from pathlib import Path

    glob_iterator = Path(folder_path).glob("*.json")
    return {
        "event_name": "upload_preannotations_from_folder_to_project",
        "properties": {
            "Annotation Count": sum(1 for _ in glob_iterator),
            "Project Type": project_type,
            "From S3": bool(args[2:3] or ("from_s3_bucket" in kwargs)),
        },
    }


def upload_images_from_folder_to_project(*args, **kwargs):
    folder_path = kwargs.get("folder_path", None)
    if not folder_path:
        folder_path = args[1]

    recursive_subfolders = kwargs.get("recursive_subfolders", None)
    if not recursive_subfolders:
        recursive_subfolders = args[6:7]
        if recursive_subfolders:
            recursive_subfolders = recursive_subfolders[0]
        else:
            recursive_subfolders = False

    extensions = kwargs.get("extensions", None)
    if not extensions:
        extensions = args[2:3]
        if extensions:
            extensions = extensions[0]
        else:
            extensions = constances.DEFAULT_IMAGE_EXTENSIONS

    exclude_file_patterns = kwargs.get("exclude_file_patterns", None)
    if not exclude_file_patterns:
        exclude_file_patterns = args[5:6]
        if exclude_file_patterns:
            exclude_file_patterns = exclude_file_patterns[0]
        else:
            exclude_file_patterns = constances.DEFAULT_FILE_EXCLUDE_PATTERNS

    from pathlib import Path
    import os

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
            "Custom Extentions": bool(args[2:3] or kwargs.get("extensions", None)),
            "Annotation Status": bool(
                args[3:4] or kwargs.get("annotation_status", None)
            ),
            "From S3": bool(args[4:5] or kwargs.get("from_s3_bucket", None)),
            "Custom Exclude Patters": bool(
                args[5:6] or kwargs.get("exclude_file_patterns", None)
            ),
        },
    }


def prepare_export(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "prepare_export",
        "properties": {
            "project_name": get_project_name(project),
            "Folder Count": bool(args[1:2] or kwargs.get("folder_names", None)),
            "Annotation Statuses": bool(
                args[2:3] or kwargs.get("annotation_statuses", None)
            ),
            "Include Fuse": bool(args[3:4] or kwargs.get("include_fuse", None)),
            "Only Pinned": bool(args[4:5] or kwargs.get("only_pinned", None)),
        },
    }


def download_export(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "download_export",
        "properties": {
            "project_name": get_project_name(project),
            "to_s3_bucket": bool(args[4:5] or kwargs.get("to_s3_bucket", None)),
        },
    }


def assign_images(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    image_names = kwargs.get("image_names", None)
    if not image_names:
        image_names = args[1]
    user = kwargs.get("user", None)
    if not user:
        user = args[2]

    contributors = controller.get_project_metadata(
        project_name=project, include_contributors=True
    ).data["contributors"]
    contributor = None
    for c in contributors:
        if c["user_id"] == user:
            contributor = c
    user_role = "ADMIN"
    if contributor["user_role"] == 3:
        user_role = "ANNOTATOR"
    if contributor["user_role"] == 4:
        user_role = "QA"
    _, folder_name = extract_project_folder(project)
    is_root = True
    if folder_name:
        is_root = False

    return {
        "event_name": "assign_images",
        "properties": {
            "project_name": get_project_name(project),
            "Assign Folder": is_root,
            "Image Count": len(image_names),
            "User Role": user_role,
        },
    }


def pin_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "pin_image",
        "properties": {
            "project_name": get_project_name(project),
            "Pin": bool(args[2:3] or ("pin" in kwargs)),
        },
    }


def set_image_annotation_status(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "set_image_annotation_status",
        "properties": {
            "project_name": get_project_name(project),
            "Annotation Status": bool(args[2:3] or ("annotation_status" in kwargs)),
        },
    }


def add_annotation_bbox_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "add_annotation_bbox_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[4:5] or ("annotation_class_attributes" in kwargs)),
            "Error": bool(args[5:6] or ("error" in kwargs)),
        },
    }


def add_annotation_point_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "add_annotation_point_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[4:5] or ("annotation_class_attributes" in kwargs)),
            "Error": bool(args[5:6] or ("error" in kwargs)),
        },
    }


def create_annotation_class(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]

    return {
        "event_name": "create_annotation_class",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[3:4] or ("attribute_groups" in kwargs)),
        },
    }


def create_annotation_classes_from_classes_json(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "create_annotation_classes_from_classes_json",
        "properties": {
            "project_name": get_project_name(project),
            "From S3": bool(args[2:3] or ("from_s3_bucket" in kwargs)),
        },
    }


def class_distribution(*args, **kwargs):
    return {
        "event_name": "class_distribution",
        "properties": {"Plot": bool(args[2:3] or ("visualize" in kwargs))},
    }


def share_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    user_role = kwargs.get("user_role", None)
    if not user_role:
        user_role = args[2]
    return {
        "event_name": "share_project",
        "properties": {
            "project_name": get_project_name(project),
            "User Role": user_role,
        },
    }


def set_project_default_image_quality_in_editor(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    image_quality_in_editor = kwargs.get("image_quality_in_editor", None)
    if not image_quality_in_editor:
        image_quality_in_editor = args[1]
    return {
        "event_name": "set_project_default_image_quality_in_editor",
        "properties": {
            "project_name": get_project_name(project),
            "Image Quality": image_quality_in_editor,
        },
    }


def get_exports(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "get_exports",
        "properties": {
            "project_name": get_project_name(project),
            "Metadata": bool(args[1:2] or ("return_metadata" in kwargs)),
        },
    }


def search_folders(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "search_folders",
        "properties": {
            "project_name": get_project_name(project),
            "Metadata": bool(args[2:3] or ("return_metadata" in kwargs)),
        },
    }


def aggregate_annotations_as_df(*args, **kwargs):

    folder_names = kwargs.get("folder_names", "empty")
    if folder_names == "empty":
        folder_names = args[5:6]
        if folder_names:
            folder_names = folder_names[0]
            if folder_names is None:
                folder_names = []

    return {
        "event_name": "aggregate_annotations_as_df",
        "properties": {"Folder Count": len(folder_names)},
    }


def delete_folders(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    folder_names = kwargs.get("folder_names", None)
    if not folder_names:
        folder_names = args[1]
    return {
        "event_name": "delete_folders",
        "properties": {
            "project_name": get_project_name(project),
            "Folder Count": len(folder_names),
        },
    }


def delete_images(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    image_names = kwargs.get("image_names", False)
    if not image_names:
        image_names = args[1]
        if image_names is None:
            res = controller.search_images(project)
            image_names = res.data
    return {
        "event_name": "delete_images",
        "properties": {
            "project_name": get_project_name(project),
            "Image Count": len(image_names),
        },
    }


def unassign_folder(*args, **kwargs):
    return {"event_name": "unassign_folder", "properties": {}}


def assign_folder(*args, **kwargs):
    users = kwargs.get("users", None)
    if not users:
        users = args[2]
    return {"event_name": "assign_folder", "properties": {"User Count": len(users)}}


def unassign_images(*args, **kwargs):
    image_names = kwargs.get("image_names", None)
    if not image_names:
        image_names = args[1]

    project = kwargs.get("project", None)
    if not project:
        project = args[0]

    _, folder_name = extract_project_folder(project)
    is_root = True
    if folder_name:
        is_root = False

    return {
        "event_name": "unassign_images",
        "properties": {"Assign Folder": is_root, "Image Count": len(image_names)},
    }


def attach_video_urls_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "attach_video_urls_to_project",
        "properties": {
            "project_name": get_project_name(project),
            "Annotation Status": bool(
                args[2:3] or kwargs.get("annotation_status", None)
            ),
        },
    }


def attach_document_urls_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0]
    return {
        "event_name": "attach_document_urls_to_project",
        "properties": {
            "project_name": get_project_name(project),
            "Annotation Status": bool(
                args[2:3] or kwargs.get("annotation_status", None)
            ),
        },
    }


def delete_annotations(*args, **kwargs):
    return {"event_name": "delete_annotations", "properties": {}}


def validate_annotations(*args, **kwargs):
    project_type = kwargs.get("project_type", None)
    if not project_type:
        project_type = args[0]
    return {
        "event_name": "validate_annotations",
        "properties": {"Project Type": project_type},
    }
