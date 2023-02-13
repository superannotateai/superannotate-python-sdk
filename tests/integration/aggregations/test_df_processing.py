import os
from pathlib import Path

from src.superannotate import SAClient
from src.superannotate import AppException
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestDF(BaseTestCase):
    PROJECT_NAME = "test df processing"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.FOLDER_PATH)

    def test_filter_instances(self):
        df = sa.aggregate_annotations_as_df(self.folder_path, self.PROJECT_TYPE)
        df = df[~(df.duplicated(["instanceId", "itemName"]))]
        df = df[df.duplicated(["trackingId"], False) & df["trackingId"].notnull()]
        self.assertEqual(len(df), 2)
        self.assertEqual(
            {df.iloc[0]["itemName"], df.iloc[1]["itemName"]},
            {"example_image_1.jpg", "example_image_2.jpg"},
        )

    def test_invalid_project_type(self):
        with self.assertRaisesRegexp(AppException, "The function is not supported for PointCloud projects."):
            sa.aggregate_annotations_as_df(self.folder_path, "PointCloud")


class TestDFWithTagInstance(BaseTestCase):
    PROJECT_TYPE = "Vector"
    FOLDER_PATH = "data_set/sample_project_vector_with_tag"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.FOLDER_PATH)

    def test_filter_instances(self):
        df = sa.aggregate_annotations_as_df(self.folder_path, self.PROJECT_TYPE)
        self.assertEqual(df.iloc[0]["type"], "tag")

