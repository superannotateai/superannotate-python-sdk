import os
import tempfile
from os.path import dirname
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestFilterInstances(BaseTestCase):
    PROJECT_NAME = "test filter instances"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    PROJECT_DESCRIPTION = "desc"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_df_to_annotations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            df = sa.aggregate_annotations_as_df(self.folder_path)
            sa.df_to_annotations(df, tmp_dir)
            df_new = sa.aggregate_annotations_as_df(tmp_dir)

            assert len(df) == len(df_new)
            for _index, row in enumerate(df.iterrows()):
                for _, row_2 in enumerate(df_new.iterrows()):
                    if row_2[1].equals(row[1]):
                        break
                    # if row_2[1]["imageName"] == "example_image_1.jpg":
                    #     print(row_2[1])
                else:
                    assert False, print("Error on ", row[1])

            sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
            )
            sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path
            )
