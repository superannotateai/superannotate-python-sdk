import os
import tempfile
from pathlib import Path

from src.superannotate import SAClient
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestAnnotationUploadVector(BaseTestCase):
    PROJECT_NAME = "Test-Upload_annotations_from_folder_to_project"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_vector_annotations_with_tag_classes"
    TEST_4_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_LARGE_FOLDER_PATH = "sample_large_json_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def data_set(self):
        return Path(__file__).parent.parent.parent

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @property
    def large_annotations_folder_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_LARGE_FOLDER_PATH)

    def test_annotation_folder_upload_download(self):
        self._attach_items()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        uploaded, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        assert len(uploaded) == 1

        annotation = sa.get_annotations(self.PROJECT_NAME, ["example_image_1.jpg"])[0]

        assert annotation["instances"][-1]["type"] == "tag"
        assert annotation["instances"][-2]["type"] == "tag"

    def test_upload_keep_true(self):
        self._attach_items()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        sa.set_annotation_statuses(
            self.PROJECT_NAME, "Completed", items=["example_image_1.jpg"]
        )
        uploaded, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, keep_status=True
        )
        assert len(uploaded) == 1
        items = sa.search_items(self.PROJECT_NAME)
        for i in items:
            if i["name"] == "example_image_1.jpg":
                assert i["annotation_status"] == "Completed"

    def test_4_annotation_folder_upload_download(self):
        self._attach_items()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        uploaded, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, os.path.join(self.data_set, self.TEST_4_FOLDER_PATH)
        )
        assert len(uploaded) == 4

    def test_upload_small_annotations_7_4_MB(self):
        sa.attach_items(
            self.PROJECT_NAME,
            [
                {"name": f"aearth_mov_00{i}.jpg", "url": f"url_{i}"}
                for i in range(1, 6)
            ],  # noqa
        )

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f"{self.large_annotations_folder_path}/classes/classes.json",
        )
        uploaded, a, b = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.large_annotations_folder_path
        )
        assert len(uploaded) == 5
        annotations = sa.get_annotations(self.PROJECT_NAME)
        assert [len(annotation["instances"]) > 1 for annotation in annotations].count(
            True
        ) == 5


class TestExportUploadVector(BaseTestCase):
    PROJECT_NAME = "Test-TestExporeExportUploadVector"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_explore_export"

    @property
    def data_set(self):
        return Path(__file__).parent.parent.parent

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_annotation_folder_upload_download(self):
        sa.attach_items(
            self.PROJECT_NAME,
            [{"name": "file_example.jpg", "url": "url_"}],
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        uploaded, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        assert len(uploaded) == 1


class TestExportUploadPixel(BaseTestCase):
    PROJECT_NAME = "Test-TestExportUploadPixel"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "PIXEL"
    TEST_FOLDER_PATH = "data_set/sample_explore_export_pixel"
    ITEM_NAME = "file_example.jpg"

    @property
    def data_set(self):
        return Path(__file__).parent.parent.parent

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_annotation_folder_upload_download(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa.attach_items(
                self.PROJECT_NAME,
                [{"name": self.ITEM_NAME, "url": "url_"}],
            )
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
            )
            uploaded, _, _ = sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path
            )
            assert len(uploaded) == 1
            export_name = sa.prepare_export(self.PROJECT_NAME)["name"]
            sa.download_export(
                project=self.PROJECT_NAME, export=export_name, folder_path=tmpdir
            )
            list_dir = os.listdir(tmpdir)
            assert f"{self.ITEM_NAME}___save.png" in list_dir
            assert f"{self.ITEM_NAME}.json" in list_dir
            assert "classes" in list_dir

            with open(f"{tmpdir}/{self.ITEM_NAME}___save.png", "rb") as f1, open(
                f"{self.folder_path}/{self.ITEM_NAME}___save.png", "rb"
            ) as f2:
                contents1 = f1.read()
                contents2 = f2.read()
                assert contents1 == contents2
