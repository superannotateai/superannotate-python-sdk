import os
from os.path import dirname
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestDF(BaseTestCase):
    PROJECT_NAME = "test df processing"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH))
        )

    def test_filter_instances(self):
        df = sa.aggregate_annotations_as_df(self.folder_path,self.PROJECT_TYPE)
        df = df[~(df.duplicated(["instanceId", "imageName"]))]
        df = df[df.duplicated(["trackingId"], False) & df["trackingId"].notnull()]
        self.assertEqual(len(df), 2)
        self.assertEqual(
            {df.iloc[0]["imageName"], df.iloc[1]["imageName"]},
            {"example_image_1.jpg", "example_image_2.jpg"},
        )
