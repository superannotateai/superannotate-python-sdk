import json
import os
from pathlib import Path

from src.superannotate import SAClient
from src.superannotate.lib.app.helpers import get_annotation_paths
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestAnnotationUploadVector(BaseTestCase):
    PROJECT_NAME = "Test-upload_annotations"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_vector_annotations_with_tag_classes"
    TEST_FOLDER_PATH_NaN = "data_set/sample_vector_annotations_with_NaN"
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
    def folder_NaN(self):
        return os.path.join(
            Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH_NaN
        )

    @property
    def large_annotations_folder_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_LARGE_FOLDER_PATH)

    @staticmethod
    def _get_annotations_from_folder(path):
        paths = get_annotation_paths(path)
        annotations = []
        for i in paths:
            annotations.append(json.load(open(i)))
        return annotations

    def test_upload_NaN_value(self):
        self._attach_items()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        annotations = self._get_annotations_from_folder(self.folder_NaN)
        _, failed, _ = sa.upload_annotations(self.PROJECT_NAME, annotations).values()
        assert len(failed) == 1

    def test_annotation_folder_upload_download(self):
        self._attach_items()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        annotations = self._get_annotations_from_folder(self.folder_path)
        uploaded, _, _ = sa.upload_annotations(self.PROJECT_NAME, annotations).values()
        assert len(uploaded) == 1

        annotation = sa.get_annotations(self.PROJECT_NAME, ["example_image_1.jpg"])[0]
        items = sa.search_items(self.PROJECT_NAME)
        for i in items:
            if i["name"] == "example_image_1.jpg":
                assert i["annotation_status"] == "InProgress"
        assert annotation["instances"][-1]["type"] == "tag"
        assert annotation["instances"][-2]["type"] == "tag"
        assert annotation["instances"][-2]["probability"] == 100
        assert annotation["instances"][-2]["creationType"] == "Preannotation"

    def test_upload_keep_true(self):
        self._attach_items()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        annotations = self._get_annotations_from_folder(self.folder_path)
        sa.set_annotation_statuses(
            self.PROJECT_NAME, "Completed", items=["example_image_1.jpg"]
        )
        uploaded, _, _ = sa.upload_annotations(
            self.PROJECT_NAME, annotations, keep_status=True
        ).values()
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
        annotations = self._get_annotations_from_folder(
            os.path.join(self.data_set, self.TEST_4_FOLDER_PATH)
        )
        uploaded, _, _ = sa.upload_annotations(
            self.PROJECT_NAME, annotations=annotations
        ).values()
        assert len(uploaded) == 4

    def test_upload_large_annotations(self):
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
        annotations = self._get_annotations_from_folder(
            self.large_annotations_folder_path
        )
        uploaded, a, b = sa.upload_annotations(self.PROJECT_NAME, annotations).values()
        assert len(uploaded) == 5
        annotations = sa.get_annotations(self.PROJECT_NAME)
        assert [len(annotation["instances"]) > 1 for annotation in annotations].count(
            True
        ) == 5
