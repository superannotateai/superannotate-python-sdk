import os
import time
from os.path import dirname

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestNeuralNetworks(BaseTestCase):
    PROJECT_NAME = "nn"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_ROOT = "data_set/consensus_benchmark/consensus_test_data"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_path(self):
        return os.path.join(
            dirname(dirname(__file__)), self.TEST_ROOT, "classes/classes.json"
        )

    @property
    def images_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_ROOT, "images")

    @property
    def annotations_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_ROOT)

    def test_neural_networks(self):
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_path
        )
        for i in range(1, 3):
            sa.create_folder(self.PROJECT_NAME, "consensus_" + str(i))

        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.images_path, annotation_status="Completed"
        )

        for i in range(1, 3):
            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME + "/consensus_" + str(i),
                self.images_path,
                annotation_status="Completed",
            )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.annotations_path
        )
        for i in range(1, 3):
            sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME + "/consensus_" + str(i),
                self.annotations_path + "/consensus_" + str(i),
            )
        time.sleep(2)
        new_model = sa.run_training(
            "some name",
            "some desc",
            "Instance Segmentation for Vector Projects",
            "Instance Segmentation (trained on COCO)",
            [f"{self.PROJECT_NAME}/consensus_1"],
            [f"{self.PROJECT_NAME}/consensus_2"],
            {"base_lr": 0.02, "images_per_batch": 8},
            False,
        )
        assert "id" in new_model
