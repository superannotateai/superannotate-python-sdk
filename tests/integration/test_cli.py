import os
import subprocess
import pytest
import pkg_resources
import tempfile
from os.path import dirname
from pathlib import Path
from unittest import TestCase

import src.superannotate as sa

try:
    CLI_VERSION = pkg_resources.get_distribution("superannotate").version
except Exception:
    CLI_VERSION = None


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
    TEST_TEXT_CSV_PATH = "data_set/csv_files/text_urls.csv"
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
    def text_csv_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_TEXT_CSV_PATH))
        )

    @property
    def video_csv_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_VIDEO_CSV_PATH))
        )

    def _create_project(self, project_type="Vector"):
        subprocess.run(
            f'superannotatecli create-project --name "{self.PROJECT_NAME}" --description gg --type {project_type}',
            check=True,
            shell=True,
        )

    @pytest.mark.skipif(CLI_VERSION and CLI_VERSION != sa.__version__,
                        reason=f"Updated package version from {CLI_VERSION} to {sa.__version__}")
    def test_create_folder(self):
        self._create_project()
        subprocess.run(
            f'superannotatecli create-folder --project "{self.PROJECT_NAME}" --name {self.FOLDER_NAME}',
            check=True,
            shell=True,
        )
        folder = sa.get_folder_metadata(
            project=self.PROJECT_NAME, folder_name=self.FOLDER_NAME
        )
        self.assertEqual(self.FOLDER_NAME, folder["name"])

    @pytest.mark.skipif(CLI_VERSION and CLI_VERSION != sa.__version__,
                        reason=f"Updated package version from {CLI_VERSION} to {sa.__version__}")
    def test_upload_images(self):
        self._create_project()
        subprocess.run(
            f'superannotatecli upload-images --project "{self.PROJECT_NAME}"'
            f" --folder {self.recursive_folder_path} "
            "--extensions=jpg "
            "--set-annotation-status QualityCheck",
            check=True,
            shell=True,
        )
        self.assertEqual(1, len(sa.search_images(self.PROJECT_NAME)))

    @pytest.mark.skipif(CLI_VERSION and CLI_VERSION != sa.__version__,
                        reason=f"Updated package version from {CLI_VERSION} to {sa.__version__}")
    def test_upload_export(self):
        self._create_project()
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test1"
            test_dir.mkdir()
            subprocess.run(
                f'superannotatecli export-project --project "{self.PROJECT_NAME}" --folder {test_dir}',
                check=True,
                shell=True,
            )
            self.assertEqual(len(list(test_dir.rglob("*.json"))), 1)
            self.assertEqual(len(list(test_dir.glob("*.jpg"))), 0)
            self.assertEqual(len(list(test_dir.glob("*.png"))), 0)

    @pytest.mark.skipif(CLI_VERSION and CLI_VERSION != sa.__version__,
                        reason=f"Updated package version from {CLI_VERSION} to {sa.__version__}")
    def test_vector_pre_annotation_folder_upload_download_cli(self):
        self._create_project()

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.vector_folder_path}/classes/classes.json"
        )
        subprocess.run(
            f'superannotatecli upload-images --project "{self.PROJECT_NAME}"'
            f" --folder {self.convertor_data_path} "
            "--extensions=jpg "
            "--set-annotation-status QualityCheck",
            check=True,
            shell=True,
        )

        subprocess.run(
            f"superannotatecli upload-preannotations "
            f'--project "{self.PROJECT_NAME}" '
            f'--folder "{self.convertor_data_path}" '
            f'--format COCO '
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

    @pytest.mark.skipif(CLI_VERSION and CLI_VERSION != sa.__version__,
                        reason=f"Updated package version from {CLI_VERSION} to {sa.__version__}")
    def test_vector_annotation_folder_upload_download_cli(self):
        self._create_project()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.vector_folder_path}/classes/classes.json"
        )
        subprocess.run(
            f"superannotatecli upload-images"
            f' --project "{self.PROJECT_NAME}"'
            f" --folder {self.convertor_data_path} "
            "--extensions=jpg "
            "--set-annotation-status QualityCheck",
            check=True,
            shell=True,
        )
        subprocess.run(
            f"superannotatecli upload-annotations "
            f'--project "{self.PROJECT_NAME}" '
            f'--folder "{self.convertor_data_path}" '
            f'--format COCO '
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

    @pytest.mark.skipif(CLI_VERSION and CLI_VERSION != sa.__version__,
                        reason=f"Updated package version from {CLI_VERSION} to {sa.__version__}")
    def test_attach_image_urls(self):
        self._create_project()
        subprocess.run(
            f"superannotatecli attach-image-urls "
            f'--project "{self.PROJECT_NAME}" '
            f"--attachments {self.image_csv_path}",
            check=True,
            shell=True,
        )

        self.assertEqual(3, len(sa.search_images(self.PROJECT_NAME)))

    @pytest.mark.skipif(CLI_VERSION and CLI_VERSION != sa.__version__,
                        reason=f"Updated package version from {CLI_VERSION} to {sa.__version__}")
    def test_attach_video_urls(self):
        self._create_project("Video")
        subprocess.run(
            f"superannotatecli attach-video-urls "
            f'--project "{self.PROJECT_NAME}" '
            f"--attachments {self.video_csv_path}",
            check=True,
            shell=True,
        )
        self.assertEqual(3, len(sa.search_images(self.PROJECT_NAME)))

    @pytest.mark.skipif(CLI_VERSION and CLI_VERSION != sa.__version__,
                        reason=f"Updated package version from {CLI_VERSION} to {sa.__version__}")
    def test_upload_videos(self):
        self._create_project()
        subprocess.run(
            f"superannotatecli upload-videos "
            f'--project "{self.PROJECT_NAME}" '
            f"--folder '{self.video_folder_path}' "
            f"--target-fps 1",
            check=True,
            shell=True,
        )
        self.assertEqual(4, len(sa.search_images(self.PROJECT_NAME)))

    def test_attach_document_urls(self):
            self._create_project("Document")
            subprocess.run(
                f"superannotatecli attach-document-urls "
                f'--project "{self.PROJECT_NAME}" '
                f"--attachments {self.image_csv_path}",
                check=True,
                shell=True,
            )
