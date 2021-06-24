import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

import fire
import src.lib.app.bin as config
from src.lib.app.interface.cli_interface import CLIFacade
from src.lib.infrastructure import controller


class SABaseException(Exception):
    # todo fix
    pass


logger = logging.getLogger("superannotate-python-sdk")

_CLI_COMMAND = Path(sys.argv[0]).name

# TODO Add help text
HELP_TEXT = ""


def ask_token():
    config_dir = Path.home() / ".superannotate"
    config_filename = "config.json"
    config_file = config_dir / config_filename
    if config_file.is_file():
        yes_no = input(f"File {config_file} exists. Do you want to overwrite? [y/n] : ")
        if yes_no != "y":
            return
    token = input("Input the team SDK token from https://app.superannotate.com/team : ")
    config_dir.mkdir(exist_ok=True)
    if config_file.is_file():
        existing_config = json.load(open(config_file))
        existing_config["token"] = token
        json.dump(existing_config, open(config_file, "w"), indent=4)
        logger.info("Configuration file %s successfully updated.", config_file)
    else:
        json.dump(
            {
                "token": token,
                "main_endpoint": "https://api.annotate.online",
                "ssl_verify": True,
            },
            open(config_file, "w"),
            indent=4,
        )
        logger.info("Configuration file %s successfully created.", config_file)


def video_upload(command_name, args):
    parser = argparse.ArgumentParser(prog=_CLI_COMMAND + " " + command_name)
    parser.add_argument("--project", required=True, help="Project name to upload")
    parser.add_argument("--folder", required=True, help="Folder from which to upload")
    parser.add_argument(
        "--recursive",
        default=False,
        action="store_true",
        help="Enables recursive subfolder upload.",
    )
    parser.add_argument(
        "--extensions",
        required=False,
        default=config.DEFAULT_VIDEO_EXTENSIONS,
        type=lambda value: value.split(","),
        help="List of video extensions to include. Default is mp4,avi,mov,webm,flv,mpg,ogg",
    )
    parser.add_argument(
        "--set-annotation-status",
        required=False,
        default="NotStarted",
        help="Set images' annotation statuses after upload. Default is NotStarted",
    )
    parser.add_argument(
        "--target-fps",
        required=False,
        default=None,
        type=float,
        help="How many frames per second need to extract from the videos (approximate)."
        "  If not specified all frames will be uploaded",
    )
    parser.add_argument(
        "--start-time",
        required=False,
        default=0.0,
        type=float,
        help="Time (in seconds) from which to start extracting frames. Default is 0.0",
    )
    parser.add_argument(
        "--end-time",
        required=False,
        default=None,
        type=float,
        help="Time (in seconds) up to which to extract frames. If it is not specified, then up to end",
    )
    args = parser.parse_args(args)

    controller.upload_videos_from_folder_to_project(
        project=args.project,
        folder_path=args.folder,
        extensions=args.extensions,
        annotation_status=args.set_annotation_status,
        recursive_subfolders=args.recursive,
        target_fps=args.target_fps,
        start_time=args.start_time,
        end_time=args.end_time,
    )


def image_upload(command_name, args):
    parser = argparse.ArgumentParser(prog=_CLI_COMMAND + " " + command_name)
    parser.add_argument("--project", required=True, help="Project name to upload")
    parser.add_argument("--folder", required=True, help="Folder from which to upload")
    parser.add_argument(
        "--recursive",
        default=False,
        action="store_true",
        help="Enables recursive subfolder upload.",
    )
    parser.add_argument(
        "--extensions",
        default=config.DEFAULT_IMAGE_EXTENSIONS,
        type=lambda value: value.split(","),
        help="List of image extensions to include. Default is jpg,jpeg,png,tif,tiff,webp,bmp",
    )
    parser.add_argument(
        "--set-annotation-status",
        required=False,
        default="NotStarted",
        help="Set images' annotation statuses after upload. Default is NotStarted",
    )
    args = parser.parse_args(args)

    controller.upload_images_from_folder_to_project(
        project=args.project,
        folder_path=args.folder,
        extensions=args.extensions,
        annotation_status=args.set_annotation_status,
        recursive_subfolders=args.recursive,
    )


def attach_image_urls(command_name, args):
    parser = argparse.ArgumentParser(prog=_CLI_COMMAND + " " + command_name)
    parser.add_argument("--project", required=True, help="Project name to upload")
    parser.add_argument(
        "--attachments", required=True, help="path to csv file on attachments metadata"
    )
    parser.add_argument(
        "--annotation_status",
        required=False,
        default="NotStarted",
        help="Set images' annotation statuses after upload. Default is NotStarted",
    )
    args = parser.parse_args(args)
    controller.attach_image_urls_to_project(
        project=args.project,
        attachments=args.attachments,
        annotation_status=args.annotation_status,
    )


def export_project(
    project, folder, annotation_statuses, include_fuse, disable_extract_zip_contents
):
    parts = project.split("/")

    if len(parts) == 1:
        project, project_folder = parts[0], None
    elif len(parts) == 2:
        project, project_folder = parts
    else:
        raise SABaseException(0, "Project should be in format <project>[/<folder>]")

    export = controller.prepare_export(
        project,
        None if project_folder is None else [project_folder],
        annotation_statuses=annotation_statuses,
        include_fuse=include_fuse,
    )
    controller.download_export(
        project, export, folder, not disable_extract_zip_contents
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        required=True,
        choices=[
            "create-project",
            "create-folder",
            "upload-images",
            "upload-videos",
            "upload-preannotations",
            "upload-annotations",
            "export-project",
        ],
        help="Available commands to superannotate CLI are",
    )
    parser.add_argument("--name", required=True, help="Project name to create")
    parser.add_argument("--name", required=True, help="Project name to create")
    parser.add_argument("--description", required=True, help="Project description")
    parser.add_argument("--type", required=True, help="Project type Vector or Pixel")
    # TODO change
    parser.add_argument("--folder", required=True, help="Folder Path")
    parser.add_argument(
        "--format",
        required=False,
        default="SuperAnnotate",
        help="Input preannotations format.",
    )
    parser.add_argument(
        "--dataset-name",
        required=False,
        help="Input annotations dataset name for COCO projects",
    )
    parser.add_argument(
        "--recursive",
        default=False,
        action="store_true",
        help="Enables recursive subfolder upload.",
    )
    parser.add_argument(
        "--attachments", required=True, help="path to csv file on attachments metadata"
    )
    parser.add_argument(
        "--task",
        required=False,
        help="Task type for COCO projects can be panoptic_segmentation (Pixel), "
        "instance_segmentation (Pixel), instance_segmentation (Vector), keypoint_detection (Vector)",
    )
    # TODO delete both
    # parser.add_argument('--name', required=True, help='Project name to create')
    # parser.add_argument('--name', required=True, help='Folder name to create')

    # TODO check changed
    parser.add_argument(
        "--extensions",
        required=False,
        default=config.DEFAULT_VIDEO_EXTENSIONS,
        type=lambda value: value.split(","),
        help="List of extensions to include. For video default is mp4,avi,mov,webm,flv,mpg,ogg, "
        "for image default is jpg,jpeg,png,tif,tiff,webp,bmp",
    )
    parser.add_argument(
        "--set-annotation-status",
        required=False,
        default="NotStarted",
        help="Set images' annotation statuses after upload. Default is NotStarted",
    )
    parser.add_argument(
        "--target-fps",
        required=False,
        default=None,
        type=float,
        help="How many frames per second need to extract from the videos (approximate). "
        " If not specified all frames will be uploaded",
    )
    parser.add_argument(
        "--start-time",
        required=False,
        default=0.0,
        type=float,
        help="Time (in seconds) from which to start extracting frames. Default is 0.0",
    )
    # Todo merge with above one
    # parser.add_argument(
    #     '--start-time',
    #     required=False,
    #     default=None,
    #     type=float,
    #     help=
    #     'Time (in seconds) up to which to extract frames. If it is not specified, then up to end'
    # )
    parser.add_argument(
        "--annotation_status",
        required=False,
        default="NotStarted",
        help="Set images' annotation statuses after upload. Default is NotStarted",
    )
    parser.add_argument(
        "--include-fuse",
        default=False,
        action="store_true",
        help="Enables fuse image export",
    )
    parser.add_argument(
        "--disable-extract-zip-contents",
        default=False,
        action="store_true",
        help="Disables export zip extraction",
    )
    parser.add_argument(
        "--annotation-statuses",
        default=None,
        type=lambda value: value.split(","),
        help="List of image annotation statuses to include in export."
        " Default is InProgress,QualityCheck,Returned,Completed",
    )
    available_commands = (
        "Available commands to superannotate CLI are: init version create-project create-folder "
        "upload-images upload-videos upload-preannotations upload-annotations export-project"
    )
    args = parser.parse_args()
    command = args.command

    if command == "create-project":
        controller.create_project(args.name, args.description, args.type)
    elif command == "create-folder":
        controller.create_folder(args.name)
    # TODO to be continued
    elif command == "upload-images":
        controller.upload_images_from_folder_to_project(
            project=args.project,
            folder_path=args.folder,
            extensions=args.extensions,
            annotation_status=args.set_annotation_status,
            recursive_subfolders=args.recursive,
        )
    elif command == "attach-image-urls":
        controller.attach_image_urls_to_project(
            project=args.project,
            attachments=args.attachments,
            annotation_status=args.annotation_status,
        )
    elif command == "upload-videos":
        controller.upload_videos_from_folder_to_project(
            project=args.project,
            folder_path=args.folder,
            extensions=args.extensions,
            annotation_status=args.set_annotation_status,
            recursive_subfolders=args.recursive,
            target_fps=args.target_fps,
            start_time=args.start_time,
            end_time=args.end_time,
        )
    elif command in ["upload-preannotations", "upload-annotations"]:
        project_metadata, folder_metadata = controller.get_project_and_folder_metadata(
            args.project
        )

        if args.format != "SuperAnnotate":
            if args.format != "COCO":
                raise controller.SABaseException(
                    0, "Not supported annotations format " + args.format
                )
            if args.dataset_name is None:
                raise controller.SABaseException(
                    0, "Dataset name should be present for COCO format upload."
                )
            if args.task is None:
                raise controller.SABaseException(
                    0, "Task name should be present for COCO format upload."
                )

            logger.info("Annotations in format %s.", args.format)
            project_type = project_metadata["type"]

            tempdir = tempfile.TemporaryDirectory()
            tempdir_path = Path(tempdir.name)
            controller.import_annotation(
                args.folder,
                tempdir_path,
                "COCO",
                args.dataset_name,
                project_type,
                args.task,
            )
            args.folder = tempdir_path
        controller.create_annotation_classes_from_classes_json(
            project_metadata, Path(args.folder) / "classes" / "classes.json"
        )
        if command == "upload-preannotations":
            controller.upload_annotations_from_folder_to_project(
                (project_metadata, folder_metadata), folder_path=args.folder
            )
        else:
            controller.upload_preannotations_from_folder_to_project(
                (project_metadata, folder_metadata), folder_path=args.folder
            )
    elif command == "init":
        ask_token()
    elif command == "export-project":
        export_project(
            args.project,
            args.folder,
            args.annotation_statuses,
            args.include_fuse,
            args.disable_extract_zip_contents,
        )
    elif command == "version":
        print(f"SuperAnnotate Python SDK version {controller.__version__}")
    else:
        raise SABaseException(
            0, f"Wrong command {command} to superannotate CLI. {available_commands}",
        )


if __name__ == "__main__":
    fire.Fire(CLIFacade)
