import os
import subprocess
import tempfile
from os.path import dirname
from pathlib import Path
from unittest import TestCase

import src.lib.app.superannotate as sa


SCRIPT_PATH = (
    "/"
    + "/".join(Path(os.path.expanduser(__file__)).parts[1:6])
    + "/lib/app/bin/superannotate.py"
)


class CLITest(TestCase):
    PROJECT_NAME = "test_cli_image_upload"
    FOLDER_NAME = "test_folder"
    TEST_CONVERTOR_PATH = (
        "data_set/converter_test/COCO/input/toSuperAnnotate/instance_segmentation"
    )
    TEST_VIDEO_PATH = "data_set/sample_videos/single"
    TEST_VECTOR_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_PIXEL_FOLDER_PATH = "data_set/sample_project_pixel"
    TEST_RECURSIVE_FOLDER_PATH = "data_set/sample_recursive_test"
    TEST_IMAGE_CSV_PATH = "data_set/csv_files/image_urls.csv"
    TEST_VIDEO_CSV_PATH = "data_set/csv_files/image_urls.csv"

    def setUp(self, *args, **kwargs):
        self.tearDown()

    def tearDown(self) -> None:
        projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
        for project in projects:
            sa.delete_project(project)

    @property
    def convertor_data_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_CONVERTOR_PATH))
        )

    @property
    def video_folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_VIDEO_PATH))
        )

    @property
    def vector_folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_VECTOR_FOLDER_PATH))
        )

    @property
    def pixel_folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_PIXEL_FOLDER_PATH))
        )

    @property
    def recursive_folder_path(self):
        return Path(
            Path(
                os.path.join(
                    dirname(dirname(__file__)), self.TEST_RECURSIVE_FOLDER_PATH
                )
            )
        )

    @property
    def image_csv_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_IMAGE_CSV_PATH))
        )

    @property
    def video_csv_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_VIDEO_CSV_PATH))
        )

    def _create_project(self, project_type="Vector"):
        subprocess.run(
            f'python {SCRIPT_PATH} create-project --name "{self.PROJECT_NAME}" --description gg --type {project_type}',
            check=True,
            shell=True,
        )

    def test_create_project(self):
        self._create_project()
        projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
        self.assertEqual(self.PROJECT_NAME, projects[0]["name"])

    def test_create_folder(self):
        self._create_project()
        subprocess.run(
            f'python {SCRIPT_PATH} create-folder --project "{self.PROJECT_NAME}" --name {self.FOLDER_NAME}',
            check=True,
            shell=True,
        )
        folder = sa.get_folder_metadata(
            project=self.PROJECT_NAME, folder_name=self.FOLDER_NAME
        )
        self.assertEqual(self.FOLDER_NAME, folder["name"])

    def test_upload_images(self):
        self._create_project()
        subprocess.run(
            f'python {SCRIPT_PATH} upload-images --project "{self.PROJECT_NAME}"'
            f" --folder {self.recursive_folder_path} "
            "--extensions=jpg "
            "--set-annotation-status QualityCheck",
            check=True,
            shell=True,
        )
        self.assertEqual(1, len(sa.search_images(self.PROJECT_NAME)))

    def test_upload_export(self):
        self._create_project()
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test1"
            test_dir.mkdir()
            subprocess.run(
                f'python {SCRIPT_PATH} export-project --project "{self.PROJECT_NAME}" --folder {test_dir}',
                check=True,
                shell=True,
            )
            self.assertEqual(len(list(test_dir.rglob("*.json"))), 1)
            self.assertEqual(len(list(test_dir.glob("*.jpg"))), 0)
            self.assertEqual(len(list(test_dir.glob("*.png"))), 0)

    def test_vector_pre_annotation_folder_upload_download_cli(self):
        self._create_project()

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.vector_folder_path}/classes/classes.json"
        )
        subprocess.run(
            f'python {SCRIPT_PATH} upload-images --project "{self.PROJECT_NAME}"'
            f" --folder {self.convertor_data_path} "
            "--extensions=jpg "
            "--set-annotation-status QualityCheck",
            check=True,
            shell=True,
        )

        s = subprocess.run(
            f"python {SCRIPT_PATH} upload-preannotations "
            f'--project "{self.PROJECT_NAME}" '
            f'--folder "{self.convertor_data_path}" '
            f'--data-set-name "instances_test"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        count_in = len(list(self.vector_folder_path.glob("*.json")))
        with tempfile.TemporaryDirectory() as temp_dir:
            for image_name in sa.search_images(self.PROJECT_NAME):
                sa.download_image_preannotations(
                    self.PROJECT_NAME, image_name, temp_dir
                )
            count_out = len(list(Path(temp_dir).glob("*.json")))
            self.assertEqual(count_in, count_out)

    def test_vector_annotation_folder_upload_download_cli(self):
        self._create_project()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.vector_folder_path}/classes/classes.json"
        )
        subprocess.run(
            f"python {SCRIPT_PATH} upload-images"
            f' --project "{self.PROJECT_NAME}"'
            f" --folder {self.convertor_data_path} "
            "--extensions=jpg "
            "--set-annotation-status QualityCheck",
            check=True,
            shell=True,
        )
        subprocess.run(
            f"python {SCRIPT_PATH} upload-annotations "
            f'--project "{self.PROJECT_NAME}" '
            f'--folder "{self.convertor_data_path}" '
            f'--data-set-name "instances_test"',
            check=True,
            shell=True,
        )
        count_in = len(list(self.vector_folder_path.glob("*.json")))
        with tempfile.TemporaryDirectory() as temp_dir:
            for image_name in sa.search_images(self.PROJECT_NAME):
                sa.download_image_annotations(self.PROJECT_NAME, image_name, temp_dir)
            count_out = len(list(Path(temp_dir).glob("*.json")))
            self.assertEqual(count_in, count_out)

    def test_attach_image_urls(self):
        self._create_project()
        subprocess.run(
            f"python {SCRIPT_PATH} attach-image-urls "
            f'--project "{self.PROJECT_NAME}" '
            f"--attachments {self.image_csv_path}",
            check=True,
            shell=True,
        )

        self.assertEqual(3, len(sa.search_images(self.PROJECT_NAME)))

    def test_attach_video_urls(self):
        self._create_project("Video")
        subprocess.run(
            f"python {SCRIPT_PATH} attach-video-urls "
            f'--project "{self.PROJECT_NAME}" '
            f"--attachments {self.video_csv_path}",
            check=True,
            shell=True,
        )
        self.assertEqual(3, len(sa.search_images(self.PROJECT_NAME)))

    def test_upload_videos(self):
        self._create_project()
        subprocess.run(
            f"python {SCRIPT_PATH} upload-videos "
            f'--project "{self.PROJECT_NAME}" '
            f"--folder '{self.video_folder_path}' "
            f"--target-fps 1",
            check=True,
            shell=True,
        )
        self.assertEqual(4, len(sa.search_images(self.PROJECT_NAME)))
