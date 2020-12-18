import argparse
import json
import logging
import sys
from pathlib import Path
import tempfile

import superannotate as sa

from .exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")

_CLI_COMMAND = Path(sys.argv[0]).name


def ask_token():
    config_dir = Path.home() / ".superannotate"
    config_filename = "config.json"
    config_file = config_dir / config_filename
    if config_file.is_file():
        yes_no = input(
            f"File {config_file} exists. Do you want to overwrite? [y/n] : "
        )
        if yes_no != "y":
            return
    token = input(
        "Input the team SDK token from https://app.superannotate.com/team : "
    )
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
                "ssl_verify": True
            },
            open(config_file, "w"),
            indent=4
        )
        logger.info("Configuration file %s successfully created.", config_file)


def main():
    available_commands = "Available commands to superannotate CLI are: init version create-project upload-images upload-videos upload-preannotations upload-annotations export-project"
    if len(sys.argv) == 1:
        raise SABaseException(
            0, "No command given to superannotate CLI. " + available_commands
        )
    command = sys.argv[1]
    further_args = sys.argv[2:]

    if command == "create-project":
        create_project(command, further_args)
    elif command == "upload-images":
        image_upload(command, further_args)
    elif command == "upload-videos":
        video_upload(command, further_args)
    elif command in ["upload-preannotations", "upload-annotations"]:
        preannotations_upload(command, further_args)
    elif command == "init":
        ask_token()
    elif command == "export-project":
        export_project(command, further_args)
    elif command == "version":
        print(f"SuperAnnotate Python SDK version {sa.__version__}")
    else:
        raise SABaseException(
            0, "Wrong command " + command + " to superannotate CLI. " +
            available_commands
        )


def _list_str(values):
    return values.split(',')


def preannotations_upload(command_name, args):
    parser = argparse.ArgumentParser(prog=_CLI_COMMAND + " " + command_name)
    parser.add_argument(
        '--project', required=True, help='Project name to upload'
    )
    parser.add_argument(
        '--folder',
        required=True,
        help=
        'Folder (SuperAnnotate format) or JSON path (COCO format) from which to upload'
    )
    parser.add_argument(
        '--format',
        required=False,
        default="SuperAnnotate",
        help='Input preannotations format.'
    )
    parser.add_argument(
        '--dataset-name',
        required=False,
        help='Input annotations dataset name for COCO projects'
    )
    parser.add_argument(
        '--task',
        required=False,
        help=
        'Task type for COCO projects can be panoptic_segmentation (Pixel), instance_segmentation (Pixel), instance_segmentation (Vector), keypoint_detection (Vector)'
    )

    args = parser.parse_args(args)

    if args.format != "SuperAnnotate":
        if args.format != "COCO":
            raise sa.SABaseException(
                0, "Not supported annotations format " + args.format
            )
        if args.dataset_name is None:
            raise sa.SABaseException(
                0, "Dataset name should be present for COCO format upload."
            )
        if args.task is None:
            raise sa.SABaseException(
                0, "Task name should be present for COCO format upload."
            )

        logger.info("Annotations in format %s.", args.format)
        project_type = sa.get_project_metadata(args.project)["type"]

        tempdir = tempfile.TemporaryDirectory()
        tempdir_path = Path(tempdir.name)
        sa.import_annotation(
            args.folder, tempdir_path, "COCO", args.dataset_name, project_type,
            args.task
        )
        args.folder = tempdir_path

    sa.create_annotation_classes_from_classes_json(
        args.project,
        Path(args.folder) / "classes" / "classes.json"
    )

    if "pre" not in command_name:
        sa.upload_annotations_from_folder_to_project(
            project=args.project, folder_path=args.folder
        )
    else:
        sa.upload_preannotations_from_folder_to_project(
            project=args.project, folder_path=args.folder
        )


def create_project(command_name, args):
    parser = argparse.ArgumentParser(prog=_CLI_COMMAND + " " + command_name)
    parser.add_argument('--name', required=True, help='Project name to create')
    parser.add_argument(
        '--description', required=True, help='Project description'
    )
    parser.add_argument(
        '--type', required=True, help='Project type Vector or Pixel'
    )
    args = parser.parse_args(args)

    sa.create_project(args.name, args.description, args.type)


def video_upload(command_name, args):
    parser = argparse.ArgumentParser(prog=_CLI_COMMAND + " " + command_name)
    parser.add_argument(
        '--project', required=True, help='Project name to upload'
    )
    parser.add_argument(
        '--folder', required=True, help='Folder from which to upload'
    )
    parser.add_argument(
        '--recursive',
        default=False,
        action='store_true',
        help='Enables recursive subfolder upload.'
    )
    parser.add_argument(
        '--extensions',
        required=False,
        default=None,
        type=_list_str,
        help=
        'List of video extensions to include. Default is mp4,avi,mov,webm,flv,mpg,ogg'
    )
    parser.add_argument(
        '--set-annotation-status',
        required=False,
        default="NotStarted",
        help=
        'Set images\' annotation statuses after upload. Default is NotStarted'
    )
    parser.add_argument(
        '--target-fps',
        required=False,
        default=None,
        type=float,
        help=
        'How many frames per second need to extract from the videos (approximate).  If not specified all frames will be uploaded'
    )
    parser.add_argument(
        '--start-time',
        required=False,
        default=0.0,
        type=float,
        help=
        'Time (in seconds) from which to start extracting frames. Default is 0.0'
    )
    parser.add_argument(
        '--end-time',
        required=False,
        default=None,
        type=float,
        help=
        'Time (in seconds) up to which to extract frames. If it is not specified, then up to end'
    )
    args = parser.parse_args(args)

    sa.upload_videos_from_folder_to_project(
        project=args.project,
        folder_path=args.folder,
        extensions=args.extensions,
        annotation_status=args.set_annotation_status,
        recursive_subfolders=args.recursive,
        target_fps=args.target_fps,
        start_time=args.start_time,
        end_time=args.end_time
    )


def image_upload(command_name, args):
    parser = argparse.ArgumentParser(prog=_CLI_COMMAND + " " + command_name)
    parser.add_argument(
        '--project', required=True, help='Project name to upload'
    )
    parser.add_argument(
        '--folder', required=True, help='Folder from which to upload'
    )
    parser.add_argument(
        '--recursive',
        default=False,
        action='store_true',
        help='Enables recursive subfolder upload.'
    )
    parser.add_argument(
        '--extensions',
        default=None,
        type=_list_str,
        help=
        'List of image extensions to include. Default is jpg,jpeg,png,tif,tiff,webp,bmp'
    )
    parser.add_argument(
        '--set-annotation-status',
        required=False,
        default="NotStarted",
        help=
        'Set images\' annotation statuses after upload. Default is NotStarted'
    )
    args = parser.parse_args(args)

    sa.upload_images_from_folder_to_project(
        project=args.project,
        folder_path=args.folder,
        extensions=args.extensions,
        annotation_status=args.set_annotation_status,
        recursive_subfolders=args.recursive
    )


def export_project(command_name, args):
    parser = argparse.ArgumentParser(prog=_CLI_COMMAND + " " + command_name)
    parser.add_argument(
        '--project', required=True, help='Project name to export'
    )
    parser.add_argument(
        '--folder', required=True, help='Folder to which export'
    )
    parser.add_argument(
        '--include-fuse',
        default=False,
        action='store_true',
        help='Enables fuse image export'
    )
    parser.add_argument(
        '--disable-extract-zip-contents',
        default=False,
        action='store_true',
        help='Disables export zip extraction'
    )
    parser.add_argument(
        '--annotation-statuses',
        default=None,
        type=_list_str,
        help=
        'List of image annotation statuses to include in export. Default is InProgress,QualityCheck,Returned,Completed'
    )
    args = parser.parse_args(args)

    export = sa.prepare_export(
        args.project, args.annotation_statuses, args.include_fuse
    )
    sa.download_export(
        args.project, export, args.folder, not args.disable_extract_zip_contents
    )


if __name__ == "__main__":
    main()
