import os
import tempfile
import time
from os.path import dirname

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestConsensus(BaseTestCase):
    PROJECT_NAME = "consensus"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    NEW_PROJECT_NAME = "new"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    MODEL_NAME = "Instance segmentation (trained on COCO)"
    TEST_EXPORT_ROOT = "data_set/consensus_benchmark/consensus_test_data"
    CONSENSUS_PREFIX = "consensus_"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def export_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_EXPORT_ROOT)

    def test_consensus(self):
        annot_types = ["polygon", "bbox", "point"]
        folder_names = ["consensus_1", "consensus_2", "consensus_3"]
        df_column_names = [
            "creatorEmail",
            "imageName",
            "instanceId",
            "area",
            "className",
            "attributes",
            "folderName",
            "score",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_export_path = str(tmpdir)

            for i in range(1, 4):
                sa.create_folder(self.PROJECT_NAME, "consensus_" + str(i))
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.export_path + "/classes/classes.json"
            )
            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME,
                self.export_path + "/images",
                annotation_status="Completed",
            )
            for i in range(1, 4):
                sa.upload_images_from_folder_to_project(
                    self.PROJECT_NAME + f"/{self.CONSENSUS_PREFIX}" + str(i),
                    self.export_path + "/images",
                    annotation_status="Completed",
                )
            time.sleep(2)
            sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, self.export_path
            )
            for i in range(1, 4):
                sa.upload_annotations_from_folder_to_project(
                    self.PROJECT_NAME + f"/{self.CONSENSUS_PREFIX}" + str(i),
                    self.export_path + f"/{self.CONSENSUS_PREFIX}" + str(i),
                )

            for annot_type in annot_types:
                res_df = sa.consensus(
                    self.PROJECT_NAME, folder_names, annot_type=annot_type
                )
                # test content of projectName column
                assert sorted(res_df["folderName"].unique()) == folder_names

                # test structure of resulting DataFrame
                assert sorted(res_df.columns) == sorted(df_column_names)

                # test lower bound of the score
                assert (res_df["score"] >= 0).all()

                # test upper bound of the score
                assert (res_df["score"] <= 1).all()

            image_names = [
                "bonn_000000_000019_leftImg8bit.png",
                "bielefeld_000000_000321_leftImg8bit.png",
            ]

            # test filtering images with given image names list
            res_images = sa.consensus(
                self.PROJECT_NAME,
                folder_names,
                export_root=temp_export_path,
                image_list=image_names,
            )

            assert sorted(res_images["imageName"].unique()) == sorted(image_names)
