import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from typing import Optional

import lib.core as constances
from lib.app.input_converters.conversion import import_annotation
from lib.app.interface.sdk_interface import SAClient
from lib.infrastructure.utils import split_project_path


class CLIFacade:
    """
    With SuperAnnotate CLI, basic tasks can be accomplished using shell commands:
    superannotatecli <command> <--arg1 val1> <--arg2 val2> [--optional_arg3 val3] [--optional_arg4] ...
    """

    @staticmethod
    def version():
        """
        To show the version of the current SDK installation
        """
        from superannotate import __version__

        print(__version__)
        sys.exit(0)

    @staticmethod
    def init(
        token: str,
        logging_level: str = "INFO",
        logging_path: str = constances.LOG_FILE_LOCATION,
    ):
        """
        To initialize CLI (and SDK) with team token
        Input the team SDK token from https://app.superannotate.com/team

        :param token: the team token
        :type token: str

        :param logging_level: logging level, default is "INFO"
        :type logging_level: str

        :param logging_path: logging path for log file
        :type logging_path: str

        """
        from configparser import ConfigParser

        os.makedirs(constances.LOG_FILE_LOCATION, exist_ok=True)
        if Path(constances.CONFIG_INI_FILE_LOCATION).exists():
            operation = "updated"
            if not input(
                f"File {constances.CONFIG_INI_FILE_LOCATION} exists. Do you want to overwrite? [y/n] : "
            ).lower() in ("y", "yes"):
                return
        else:
            operation = "created"
        config_parser = ConfigParser()
        config_parser.optionxform = str
        config_parser["DEFAULT"] = {
            "SA_TOKEN": token,
            "LOGGING_LEVEL": logging_level,
            "LOGGING_PATH": logging_path,
        }
        with open(constances.CONFIG_INI_FILE_LOCATION, "w") as configfile:
            config_parser.write(configfile)
        print(f"Configuration file successfully {operation}.")
        sys.exit(0)

    def create_project(self, name: str, description: str, type: str):
        """
        To create a new project
        """
        SAClient().create_project(name, description, type)

    def create_folder(self, project: str, name: str):
        """
        To create a new folder
        """
        SAClient().create_folder(project, name)
        sys.exit(0)

    def upload_images(
        self,
        project: str,
        folder: str,
        extensions: str = constances.DEFAULT_IMAGE_EXTENSIONS,
        set_annotation_status: str = None,
        exclude_file_patterns=constances.DEFAULT_FILE_EXCLUDE_PATTERNS,
        recursive_subfolders=False,
        image_quality_in_editor=None,
    ):
        """
        To upload images from folder to project use:

        If optional argument recursive is given then subfolders of <folder_path> are also
         recursively scanned for available images.
        Optional argument extensions accepts comma separated list of image extensions to look for.
        If the argument is not given then value jpg,jpeg,png,tif,tiff,webp,bmp is assumed.
        """
        if not isinstance(extensions, list):
            extensions = extensions.split(",")
        SAClient().upload_images_from_folder_to_project(
            project,
            folder_path=folder,
            extensions=extensions,
            annotation_status=set_annotation_status,
            exclude_file_patterns=exclude_file_patterns,
            recursive_subfolders=recursive_subfolders,
            image_quality_in_editor=image_quality_in_editor,
        )
        sys.exit(0)

    def export_project(
        self,
        project,
        folder,
        include_fuse=False,
        disable_extract_zip_contents=False,
        annotation_statuses=None,
    ):
        project_name, folder_name = split_project_path(project)
        folders = None
        if not annotation_statuses:
            annotation_statuses = []
        if folder_name:
            folders = [folder_name]
        export_res = SAClient().prepare_export(
            project=project_name,
            folder_names=folders,
            include_fuse=include_fuse,
            annotation_statuses=annotation_statuses,
        )
        export_name = export_res["name"]

        SAClient().download_export(
            project=project_name,
            export=export_name,
            folder_path=folder,
            extract_zip_contents=not disable_extract_zip_contents,
            to_s3_bucket=False,
        )
        sys.exit(0)

    def upload_annotations(
        self, project, folder, dataset_name=None, task=None, format=None
    ):
        """
        To upload annotations from folder to project use
        Optional argument format accepts input annotation format. It can have COCO or SuperAnnotate values.
        If the argument is not given then SuperAnnotate (the native annotation format) is assumed.
        Only when COCO format is specified dataset-name and task arguments are required.
        dataset-name specifies JSON filename (without extension) in <folder_path>.
        task specifies the COCO task for conversion. Please see import_annotation_format for more details.
        """
        self._upload_annotations(
            project=project,
            folder=folder,
            format=format,
            dataset_name=dataset_name,
            task=task,
        )
        sys.exit(0)

    def _upload_annotations(self, project, folder, format, dataset_name, task):
        project_folder_name = project
        project_name, folder_name = split_project_path(project)
        project = SAClient().controller.get_project(project_name)
        if not format:
            format = "SuperAnnotate"
        if not dataset_name and format == "COCO":
            raise Exception("Data-set name is required")
        elif not dataset_name:
            dataset_name = ""
        if not task:
            task = "object_detection"
        annotations_path = folder
        with tempfile.TemporaryDirectory() as temp_dir:
            if format != "SuperAnnotate":
                import_annotation(
                    input_dir=folder,
                    output_dir=temp_dir,
                    dataset_format=format,
                    dataset_name=dataset_name,
                    project_type=project.type.name,
                    task=task,
                )
                annotations_path = temp_dir

            SAClient().upload_annotations_from_folder_to_project(
                project_folder_name, annotations_path
            )
        sys.exit(0)

    def attach_image_urls(
        self,
        project: str,
        attachments: str,
        annotation_status: Optional[Any] = "NotStarted",
    ):
        """
        To attach image URLs to project use:
        """

        SAClient().attach_items(
            project=project,
            attachments=attachments,
            annotation_status=annotation_status,
        )
        sys.exit(0)

    def attach_video_urls(
        self,
        project: str,
        attachments: str,
        annotation_status: Optional[Any] = "NotStarted",
    ):
        SAClient().attach_items(
            project=project,
            attachments=attachments,
            annotation_status=annotation_status,
        )
        sys.exit(0)

    @staticmethod
    def attach_document_urls(
        project: str, attachments: str, annotation_status: Optional[Any] = "NotStarted"
    ):
        SAClient().attach_items(
            project=project,
            attachments=attachments,
            annotation_status=annotation_status,
        )
        sys.exit(0)

    def upload_videos(
        self,
        project,
        folder,
        target_fps=None,
        recursive=False,
        extensions=constances.DEFAULT_VIDEO_EXTENSIONS,
        set_annotation_status=None,
        start_time=0.0,
        end_time=None,
    ):
        """
        To upload videos from folder to project use
        If optional argument recursive is given then subfolders of <folder_path> are also recursively scanned for available videos.
        Optional argument extensions accepts comma separated list of image extensions to look for.
        If the argument is not given then value mp4,avi,mov,webm,flv,mpg,ogg is assumed.
        target-fps specifies how many frames per second need to extract from the videos (approximate).
        If not specified all frames will be uploaded.
        start-time specifies time (in seconds) from which to start extracting frames, default is 0.0.
        end-time specifies time (in seconds) up to which to extract frames. If it is not specified, then up to end is assumed.
        """

        SAClient().upload_videos_from_folder_to_project(
            project=project,
            folder_path=folder,
            extensions=extensions,
            exclude_file_patterns=(),
            recursive_subfolders=recursive,
            target_fps=target_fps,
            start_time=start_time,
            end_time=end_time,
            annotation_status=set_annotation_status,
            image_quality_in_editor=None,
        )
        sys.exit(0)
