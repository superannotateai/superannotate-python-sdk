import json
import os
import tempfile
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
    TEST_4_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_BIG_FOLDER_PATH = "sample_big_json_vector"

    IMAGE_NAME = "example_image_1.jpg"

    @property
    def data_set(self):
        return Path(__file__).parent.parent.parent

    @property
    def big_annotations_folder_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_BIG_FOLDER_PATH)

    @staticmethod
    def _get_annotations_from_folder(path):
        paths = get_annotation_paths(path)
        annotations = []
        for i in paths:
            annotations.append(json.load(open(i)))
        return annotations

    def test_large_annotations_upload_get_download(self):
        items_to_attach = [
            {"name": f"aearth_mov_00{i}.jpg", "url": f"url_{i}"} for i in range(1, 6)
        ]
        sa.attach_items(
            self.PROJECT_NAME,
            items_to_attach,
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f"{self.big_annotations_folder_path}/classes/classes.json",
        )
        annotations = self._get_annotations_from_folder(
            self.big_annotations_folder_path
        )
        with self.assertLogs("sa", level="INFO") as cm:
            uploaded, _, _ = sa.upload_annotations(
                self.PROJECT_NAME, annotations
            ).values()
            assert (
                "INFO:sa:Uploading 5/5 annotations to the project Test-upload_annotations."
                == cm.output[0]
            )
            assert len(uploaded) == 5

        with self.assertLogs("sa", level="INFO") as cm:
            annotations = sa.get_annotations(self.PROJECT_NAME)
            assert (
                "INFO:sa:Getting 5 annotations from Test-upload_annotations."
                == cm.output[0]
            )
            assert len(annotations) == 5
            assert [
                len(annotation["instances"]) > 1 for annotation in annotations
            ].count(True) == 4

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertLogs("sa", level="INFO") as cm:
                sa.download_annotations(self.PROJECT_NAME, tmpdir)
                assert cm.output[0].startswith(
                    "INFO:sa:Downloading the annotations of the requested items to /var/"
                )
                assert cm.output[0].endswith("This might take a while…")

            for item_name in items_to_attach:
                annotation = self._get_annotations_from_folder(
                    f"{tmpdir}/{os.listdir(tmpdir)[0]}/{items_to_attach[0]['name']}___objects.json"
                )
                for i in annotations:
                    if i["metadata"]["name"] == item_name:
                        assert i == annotation
