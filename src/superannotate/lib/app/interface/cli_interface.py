import concurrent.futures
import json
import logging
import os
import sys
import tempfile
import uuid
from collections import Counter
from collections import namedtuple
from io import BytesIO
from pathlib import Path
from typing import Any
from typing import Optional

import lib.core as constances
import pandas as pd
from lib import __file__ as lib_path
from lib.app.helpers import get_annotation_paths
from lib.app.helpers import split_project_path
from lib.app.input_converters.conversion import import_annotation
from lib.app.interface.base_interface import BaseInterfaceFacade
from lib.app.serializers import ImageSerializer
from lib.core.entities import ConfigEntity
from lib.infrastructure.repositories import ConfigRepository
from tqdm import tqdm

logger = logging.getLogger("superannotate-python-sdk")


class CLIFacade(BaseInterfaceFacade):
    """
    With SuperAnnotate CLI, basic tasks can be accomplished using shell commands:
    superannotatecli <command> <--arg1 val1> <--arg2 val2> [--optional_arg3 val3] [--optional_arg4] ...
    """

    @staticmethod
    def version():
        """
        To show the version of the current SDK installation
        """
        with open(
            f"{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(lib_path))))}/version.py"
        ) as f:
            version = f.read().rstrip()[15:-1]
            print(version)
        sys.exit(0)

    @staticmethod
    def init():
        """
        To initialize CLI (and SDK) with team token
        """
        repo = ConfigRepository()
        config = repo.get_one(uuid=constances.TOKEN_UUID)
        if config:
            if not input(
                f"File {config} exists. Do you want to overwrite? [y/n] : "
            ).lower() in ("y", "yes"):
                return
        token = input(
            "Input the team SDK token from https://app.superannotate.com/team : "
        )
        config_entity = ConfigEntity(uuid=constances.TOKEN_UUID, value=token)
        repo.insert(config_entity)
        if config:
            print("Configuration file successfully updated.")
        else:
            print("Configuration file successfully created.")
        sys.exit(0)

    def create_project(self, name: str, description: str, type: str):
        """
        To create a new project
        """
        response = self.controller.create_project(name, description, type)
        if response.errors:
            return response.errors
        return response.data

    def create_folder(self, project: str, name: str):
        """
        To create a new folder
        """
        response = self.controller.create_folder(project=project, folder_name=name)
        if response.errors:
            logger.critical(response.errors)
        sys.exit(0)

    def upload_images(
        self,
        project: str,
        folder: str,
        extensions: str = constances.DEFAULT_IMAGE_EXTENSIONS,
        set_annotation_status: str = constances.AnnotationStatus.NOT_STARTED.name,
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
        uploaded_image_entities = []
        failed_images = []
        project_name, folder_name = split_project_path(project)
        ProcessedImage = namedtuple("ProcessedImage", ["uploaded", "path", "entity"])

        def upload_image(image_path: str):
            with open(image_path, "rb") as image:
                image_bytes = BytesIO(image.read())
                upload_response = self.controller.upload_image_to_s3(
                    project_name=project_name,
                    image_path=image_path,
                    image_bytes=image_bytes,
                    folder_name=folder_name,
                    image_quality_in_editor=image_quality_in_editor,
                )

                if not upload_response.errors and upload_response.data:
                    entity = upload_response.data
                    return ProcessedImage(
                        uploaded=True, path=entity.path, entity=entity
                    )
                else:
                    return ProcessedImage(uploaded=False, path=image_path, entity=None)

        paths = []

        if isinstance(extensions,str):
            extensions = extensions.strip().split(",")

        for extension in extensions:
            if recursive_subfolders:
                paths += list(Path(folder).rglob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    paths += list(Path(folder).rglob(f"*.{extension.upper()}"))
            else:
                paths += list(Path(folder).glob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    paths += list(Path(folder).glob(f"*.{extension.upper()}"))

        filtered_paths = []
        for path in paths:
            not_in_exclude_list = [
                x not in Path(path).name for x in exclude_file_patterns
            ]
            if all(not_in_exclude_list):
                filtered_paths.append(path)

        duplication_counter = Counter(filtered_paths)
        images_to_upload, duplicated_images = (
            set(filtered_paths),
            [item for item in duplication_counter if duplication_counter[item] > 1],
        )
        with tqdm(total=len(images_to_upload)) as progress_bar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                results = [
                    executor.submit(upload_image, image_path)
                    for image_path in images_to_upload
                ]
                for future in concurrent.futures.as_completed(results):
                    processed_image = future.result()
                    if processed_image.uploaded and processed_image.entity:
                        uploaded_image_entities.append(processed_image.entity)
                    else:
                        failed_images.append(processed_image.path)
                    progress_bar.update(1)

        for i in range(0, len(uploaded_image_entities), 500):
            self.controller.upload_images(
                project_name=project_name,
                folder_name=folder_name,
                images=uploaded_image_entities[i : i + 500],  # noqa: E203
                annotation_status=set_annotation_status,
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
        if folder_name:
            folders = [folder_name]
        export_res = self.controller.prepare_export(
            project_name, folders, include_fuse, False, annotation_statuses
        )
        export_name = export_res.data["name"]
        self.controller.download_export(
            project_name=project_name,
            export_name=export_name,
            folder_path=folder,
            extract_zip_contents=not disable_extract_zip_contents,
            to_s3_bucket=False,
        )
        sys.exit(0)

    def upload_preannotations(
        self, project, folder, data_set_name=None, task=None, format=None
    ):
        """
        To upload preannotations from folder to project use
        Optional argument format accepts input annotation format. It can have COCO or SuperAnnotate values.
         If the argument is not given then SuperAnnotate (the native annotation format) is assumed.
        Only when COCO format is specified dataset-name and task arguments are required.
        dataset-name specifies JSON filename (without extension) in <folder_path>.
        task specifies the COCO task for conversion. Please see import_annotation_format for more details.
        The annotation classes will be created during the execution of this command.
        """
        self._upload_annotations(
            project=project,
            folder=folder,
            format=format,
            data_set_name=data_set_name,
            task=task,
            pre=True,
        )
        sys.exit(0)

    def upload_annotations(
        self, project, folder, data_set_name=None, task=None, format=None
    ):
        """
        To upload annotations from folder to project use
        Optional argument format accepts input annotation format. It can have COCO or SuperAnnotate values.
        If the argument is not given then SuperAnnotate (the native annotation format) is assumed.
        Only when COCO format is specified dataset-name and task arguments are required.
        dataset-name specifies JSON filename (without extension) in <folder_path>.
        task specifies the COCO task for conversion. Please see import_annotation_format for more details.
        The annotation classes will be created during the execution of this command.
        """
        self._upload_annotations(
            project=project,
            folder=folder,
            format=format,
            data_set_name=data_set_name,
            task=task,
            pre=False,
        )
        sys.exit(0)

    def _upload_annotations(
        self, project, folder, format, data_set_name, task, pre=True
    ):
        project_name, folder_name = split_project_path(project)
        project = self.controller.get_project_metadata(project_name=project_name).data
        if not format:
            format = "SuperAnnotate"
        if not data_set_name and format == "COCO":
            raise Exception("Data-set name is required")
        elif not data_set_name:
            data_set_name = ""
        if not task:
            task = "object_detection"

        with tempfile.TemporaryDirectory() as temp_dir:
            import_annotation(
                input_dir=folder,
                output_dir=temp_dir,
                dataset_format=format,
                dataset_name=data_set_name,
                project_type=constances.ProjectType.get_name(
                    project["project"].project_type
                ),
                task=task,
            )
            classes_path = f"{temp_dir}/classes/classes.json"
            self.controller.create_annotation_classes(
                project_name=project_name,
                annotation_classes=json.load(open(classes_path)),
            )
            annotation_paths = get_annotation_paths(temp_dir)
            chunk_size = 10
            with tqdm(total=len(annotation_paths)) as progress_bar:
                for i in range(0, len(annotation_paths), chunk_size):
                    response = self.controller.upload_annotations_from_folder(
                        project_name=project["project"].name,
                        folder_name=folder_name,
                        folder_path=temp_dir,
                        annotation_paths=annotation_paths[
                            i : i + chunk_size  # noqa: E203
                        ],
                        is_pre_annotations=pre,
                    )
                    if response.errors:
                        logger.warning(response.errors)
                    progress_bar.update()
        sys.exit(0)

    def attach_image_urls(
        self, project: str, attachments: str, annotation_status: Optional[Any] = None
    ):
        """
        To attach image URLs to project use:
        """
        self._attach_urls(project, attachments, annotation_status)
        sys.exit(0)

    def attach_video_urls(
        self, project: str, attachments: str, annotation_status: Optional[Any] = None
    ):
        self._attach_urls(project, attachments, annotation_status)
        sys.exit(0)

    def _attach_urls(
        self, project: str, attachments: str, annotation_status: Optional[Any] = None
    ):
        project_name, folder_name = split_project_path(project)

        image_data = pd.read_csv(attachments, dtype=str)
        image_data = image_data[~image_data["url"].isnull()]
        for ind, _ in image_data[image_data["name"].isnull()].iterrows():
            image_data.at[ind, "name"] = str(uuid.uuid4())

        image_data = pd.DataFrame(image_data, columns=["name", "url"])
        img_names_urls = image_data.rename(columns={"url": "path"}).to_dict(
            orient="records"
        )
        list_of_not_uploaded = []
        duplicate_images = []
        for i in range(0, len(img_names_urls), 500):
            response = self.controller.attach_urls(
                project_name=project_name,
                folder_name=folder_name,
                files=ImageSerializer.deserialize(
                    img_names_urls[i : i + 500]  # noqa: E203
                ),
                annotation_status=annotation_status,
            )
            if response.errors:
                list_of_not_uploaded.append(response.data[0])
                duplicate_images.append(response.data[1])

        list_of_uploaded = [
            image["name"]
            for image in img_names_urls
            if image["name"] not in list_of_not_uploaded
        ]

        return list_of_uploaded, list_of_not_uploaded, duplicate_images

    def upload_videos(
        self,
        project,
        folder,
        target_fps=1,
        recursive=False,
        extensions=constances.DEFAULT_VIDEO_EXTENSIONS,
        set_annotation_status=constances.AnnotationStatus.NOT_STARTED.name,
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
        project_name, folder_name = split_project_path(project)

        uploaded_image_entities = []
        failed_images = []

        def _upload_image(image_path: str) -> str:
            with open(image_path, "rb") as image:
                image_bytes = BytesIO(image.read())
                upload_response = self.controller.upload_image_to_s3(
                    project_name=project_name,
                    image_path=image_path,
                    image_bytes=image_bytes,
                    folder_name=folder_name,
                )
                if not upload_response.errors:
                    uploaded_image_entities.append(upload_response.data)
                else:
                    return image_path

        video_paths = []
        for extension in extensions:
            if not recursive:
                video_paths += list(Path(folder).glob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    video_paths += list(Path(folder).glob(f"*.{extension.upper()}"))
            else:
                video_paths += list(Path(folder).rglob(f"*.{extension.lower()}"))
                if os.name != "nt":
                    video_paths += list(Path(folder).rglob(f"*.{extension.upper()}"))
        video_paths = [str(path) for path in video_paths]

        for path in video_paths:
            with tempfile.TemporaryDirectory() as temp_path:
                res = self.controller.extract_video_frames(
                    project_name=project_name,
                    folder_name=folder_name,
                    video_path=path,
                    extract_path=temp_path,
                    target_fps=int(target_fps),
                    start_time=float(start_time),
                    end_time=end_time if not end_time else float(end_time),
                    annotation_status=set_annotation_status,
                )
                if not res.errors:
                    extracted_frame_paths = res.data
                    for image_path in extracted_frame_paths:
                        failed_images.append(_upload_image(image_path))
        for i in range(0, len(uploaded_image_entities), 500):
            self.controller.upload_images(
                project_name=project_name,
                folder_name=folder_name,
                images=uploaded_image_entities[i : i + 500],  # noqa: E203
                annotation_status=set_annotation_status,
            )
        sys.exit(0)
