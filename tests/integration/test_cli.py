import os
import tempfile
from os.path import dirname
from pathlib import Path
from unittest import TestCase

import pkg_resources

from src.superannotate import SAClient
from src.superannotate.lib.app.interface.cli_interface import CLIFacade

sa = SAClient()

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
        self._cli = CLIFacade()
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

    @staticmethod
    def safe_run(method, *args, **kwargs):
        try:
            method(*args, **kwargs)
        except SystemExit:
            pass

    def _create_project(self, project_type="Vector"):
        self.safe_run(self._cli.create_project, name=self.PROJECT_NAME, description="gg", type=project_type)

    def test_create_folder(self):
        self._create_project()
        self.safe_run(self._cli.create_folder, project=self.PROJECT_NAME, name=self.FOLDER_NAME)
        folder = sa.get_folder_metadata(
            project=self.PROJECT_NAME, folder_name=self.FOLDER_NAME
        )
        self.assertEqual(self.FOLDER_NAME, folder["name"])

    def test_upload_images(self):
        self._create_project()
        self.safe_run(self._cli.upload_images, project=self.PROJECT_NAME, folder=str(self.recursive_folder_path),
                      extensions="jpg",
                      set_annotation_status="QualityCheck")
        self.assertEqual(1, len(sa.search_items(self.PROJECT_NAME)))

    def test_upload_export(self):
        self._create_project()
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test1"
            test_dir.mkdir()
            self.safe_run(self._cli.export_project, project=self.PROJECT_NAME, folder=test_dir)
            self.assertEqual(len(list(test_dir.rglob("*.json"))), 1)
            self.assertEqual(len(list(test_dir.glob("*.jpg"))), 0)
            self.assertEqual(len(list(test_dir.glob("*.png"))), 0)

    def test_vector_pre_annotation_folder_upload_download_cli(self):
        self._create_project()

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.vector_folder_path}/classes/classes.json"
        )
        self.safe_run(self._cli.upload_images, project=self.PROJECT_NAME, folder=str(self.convertor_data_path),
                      extensions="jpg",
                      set_annotation_status="QualityCheck")
        self.safe_run(self._cli.upload_preannotations, project=self.PROJECT_NAME, folder=str(self.convertor_data_path),
                      format="COCO",
                      dataset_name="instances_test")

    def test_vector_annotation_folder_upload_download_cli(self):
        self._create_project()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.vector_folder_path}/classes/classes.json"
        )
        self.safe_run(self._cli.upload_images, project=self.PROJECT_NAME, folder=str(self.convertor_data_path),
                      extensions="jpg",
                      set_annotation_status="QualityCheck")
        self.safe_run(self._cli.upload_annotations, project=self.PROJECT_NAME, folder=str(self.convertor_data_path),
                      format="COCO",
                      dataset_name="instances_test")

        count_in = len(list(self.vector_folder_path.glob("*.json")))
        with tempfile.TemporaryDirectory() as temp_dir:
            for image in sa.search_items(self.PROJECT_NAME):
                image_name = image["name"]
                sa.download_image_annotations(self.PROJECT_NAME, image_name, temp_dir)
            count_out = len(list(Path(temp_dir).glob("*.json")))
            self.assertEqual(count_in, count_out)

    def test_attach_image_urls(self):
        self._create_project()
        self.safe_run(self._cli.attach_image_urls, self.PROJECT_NAME, str(self.video_csv_path))
        self.assertEqual(3, len(sa.search_items(self.PROJECT_NAME)))

    def test_attach_video_urls(self):
        self._create_project("Video")
        self.safe_run(self._cli.attach_video_urls, self.PROJECT_NAME, str(self.video_csv_path))
        self.assertEqual(3, len(sa.search_items(self.PROJECT_NAME)))

    def test_upload_videos(self):
        self._create_project()
        self.safe_run(self._cli.upload_videos, self.PROJECT_NAME, str(self.video_folder_path))
        self.assertEqual(121, len(sa.search_items(self.PROJECT_NAME)))

    def test_attach_document_urls(self):
        self._create_project("Document")
        self.safe_run(self._cli.attach_document_urls, self.PROJECT_NAME, str(self.video_csv_path))
        self.assertEqual(3, len(sa.search_items(self.PROJECT_NAME)))
