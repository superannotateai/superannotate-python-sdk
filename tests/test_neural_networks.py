import time
from pathlib import Path

import superannotate as sa

test_root = Path().resolve() / 'tests'
project_name = "training"


def test_run_training():
    # export_path = test_root / 'consensus_benchmark' / 'consensus_test_data'
    # if len(sa.search_projects(project_name)) != 0:
    #     sa.delete_project(project_name)
    # time.sleep(2)
    #
    # sa.create_project(project_name, "test bench", "Vector")
    # time.sleep(2)
    # for i in range(1, 4):
    #     sa.create_folder(project_name, "consensus_" + str(i))
    # time.sleep(2)
    # sa.create_annotation_classes_from_classes_json(
    #     project_name, export_path / 'classes' / 'classes.json'
    # )
    # sa.upload_images_from_folder_to_project(
    #     project_name, export_path / "images", annotation_status="Completed"
    # )
    # for i in range(1, 4):
    #     sa.upload_images_from_folder_to_project(
    #         project_name + '/consensus_' + str(i),
    #         export_path / "images",
    #         annotation_status="Completed"
    #     )
    # sa.upload_annotations_from_folder_to_project(project_name, export_path)
    # for i in range(1, 4):
    #     sa.upload_annotations_from_folder_to_project(
    #         project_name + '/consensus_' + str(i),
    #         export_path / ('consensus_' + str(i))
    #     )
    # time.sleep(2)
    new_model = sa.run_training(
        "some name",
        "some desc",
        "Instance Segmentation for Vector Projects",
        "Instance Segmentation (trained on COCO)",
        [f"{project_name}/consensus_1"],
        [f"{project_name}/consensus_2"],
        {
            "base_lr": 0.02,
            "images_per_batch": 8
        },
        False
    )

    assert "id" in new_model
