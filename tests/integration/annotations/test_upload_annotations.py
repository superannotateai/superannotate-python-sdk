import json
import os
import tempfile
from pathlib import Path

from src.superannotate import AppException
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
        with self.assertWarns(DeprecationWarning):
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


class MultiModalUploadDownloadAnnotations(BaseTestCase):
    PROJECT_NAME = "TestMultimodalUploadAnnotations"
    PROJECT_TYPE = "Multimodal"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    BASE_PATH = Path(__file__).parent.parent.parent
    DATA_SET_PATH = BASE_PATH / "data_set"

    EDITOR_TEMPLATE_PATH = DATA_SET_PATH / "editor_templates/form1.json"
    JSONL_ANNOTATIONS_PATH = DATA_SET_PATH / "multimodal/annotations/jsonl/form1.jsonl"
    JSONL_ANNOTATIONS_WITH_CATEGORIES_PATH = (
        DATA_SET_PATH / "multimodal/annotations/jsonl/form1_with_categories.jsonl"
    )
    CLASSES_TEMPLATE_PATH = DATA_SET_PATH / "editor_templates" / "form1_classes.json"
    MULTIMODAL_FORM = {
        "components": [
            {
                "id": "r_qx07c6",
                "type": "audio",
                "permissions": [],
                "hasTooltip": False,
                "exclude": False,
                "label": "",
                "value": "",
            }
        ],
        "readme": "",
    }

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            "Multimodal",
            settings=[
                {"attribute": "CategorizeItems", "value": 1},
                {"attribute": "TemplateState", "value": 1},
            ],
            form=self.MULTIMODAL_FORM,
        )
        project = sa.controller.get_project(self.PROJECT_NAME)
        # todo check
        # time.sleep(4)
        with open(self.EDITOR_TEMPLATE_PATH) as f:
            res = sa.controller.service_provider.projects.attach_editor_template(
                sa.controller.team, project, template=json.load(f)
            )
            assert res.ok
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.CLASSES_TEMPLATE_PATH
        )

    def test_upload_to_root(self):
        with open(self.JSONL_ANNOTATIONS_PATH) as f:
            data = [json.loads(line) for line in f]
            data[0]["metadata"]["folder_name"] = ""
            data[0]["metadata"]["folder_name"] = "root"
            del data[0]["metadata"]["folder_name"]
            response = sa.upload_annotations(
                self.PROJECT_NAME, annotations=data, data_spec="multimodal"
            )
            assert len(response["succeeded"]) == 3
            annotations = sa.get_annotations(
                f"{self.PROJECT_NAME}", data_spec="multimodal"
            )
            assert all([len(i["data"].keys()) == 3 for i in annotations]) is True

    def test_upload_from_root_to_folder(self):
        with open(self.JSONL_ANNOTATIONS_PATH) as f:
            data = [json.loads(line) for line in f]
            response = sa.upload_annotations(
                self.PROJECT_NAME, annotations=data, data_spec="multimodal"
            )
            assert len(response["succeeded"]) == 3
            annotations = sa.get_annotations(
                f"{self.PROJECT_NAME}/test_folder", data_spec="multimodal"
            )
            assert all([len(i["data"].keys()) == 3 for i in annotations]) is True
            folders = sa.search_folders(self.PROJECT_NAME)
            assert len(folders) == 1
            sa.upload_annotations(
                self.PROJECT_NAME, annotations=data, data_spec="multimodal"
            )
            assert len(folders) == 1

    def test_error_upload_from_folder_to_folder_(self):
        with open(self.JSONL_ANNOTATIONS_PATH) as f:
            data = [json.loads(line) for line in f]
            sa.create_folder(self.PROJECT_NAME, "tmp")
            with self.assertRaisesRegexp(
                AppException,
                "You can't include a folder when uploading from within a folder.",
            ):
                sa.upload_annotations(
                    f"{self.PROJECT_NAME}/tmp", annotations=data, data_spec="multimodal"
                )

    def test_upload_with_categories(self):
        with open(self.JSONL_ANNOTATIONS_WITH_CATEGORIES_PATH) as f:
            data = [json.loads(line) for line in f]
            sa.upload_annotations(
                f"{self.PROJECT_NAME}", annotations=data, data_spec="multimodal"
            )
            annotations = sa.get_annotations(
                f"{self.PROJECT_NAME}/test_folder", data_spec="multimodal"
            )
            assert len(annotations) == 3

    def test_upload_with_integer_names(self):
        data = []
        with open(self.JSONL_ANNOTATIONS_WITH_CATEGORIES_PATH) as f:
            for i, line in enumerate(f):
                _data = json.loads(line)
                _data["metadata"]["name"] = i
                data.append(_data)
            res = sa.upload_annotations(
                f"{self.PROJECT_NAME}", annotations=data, data_spec="multimodal"
            )
            assert len(res["failed"]) == 3
            with self.assertRaisesRegexp(AppException, "Folder not found."):
                sa.get_annotations(
                    f"{self.PROJECT_NAME}/test_folder", data_spec="multimodal"
                )

    def test_download_annotations(self):
        with open(self.JSONL_ANNOTATIONS_PATH) as f:
            data = [json.loads(line) for line in f]
            sa.upload_annotations(
                self.PROJECT_NAME, annotations=data, data_spec="multimodal"
            )

        annotations = sa.get_annotations(
            f"{self.PROJECT_NAME}/test_folder", data_spec="multimodal"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            sa.download_annotations(
                f"{self.PROJECT_NAME}/test_folder", path=tmpdir, data_spec="multimodal"
            )
            downloaded_files = list(Path(f"{tmpdir}/test_folder").glob("*.json"))
            assert len(downloaded_files) > 0, "No annotations were downloaded"
            downloaded_data = []
            for file_path in downloaded_files:
                with open(file_path) as f:
                    downloaded_data.append(json.load(f))

            assert len(downloaded_data) == len(
                annotations
            ), "Mismatch in annotation count"
            for a in downloaded_data:
                assert a in annotations, "Mismatch in annotation count"
