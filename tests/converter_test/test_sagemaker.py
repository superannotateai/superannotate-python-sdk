from pathlib import Path
import superannotate as sa


def sagemaker_object_detection(tmpdir):
    out_dir = tmpdir / "object_detection"
    sa.import_annotation_format(
        'tests/converter_test/SageMaker/input/toSuperAnnotate/object_detection',
        str(out_dir), 'SageMaker', 'test-obj-detect', 'Vector',
        'object_detection', 'Web'
    )

    project_name = "sagemaker_object_detection"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir + "/classes/classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)

    return 0


def sagemaker_instance_segmentation(tmpdir):
    out_dir = tmpdir / "instance_segmentation"
    sa.import_annotation_format(
        'tests/converter_test/SageMaker/input/toSuperAnnotate/instance_segmentation',
        str(out_dir), 'SageMaker', 'test-obj-detect', 'Pixel',
        'instance_segmentation', 'Desktop'
    )

    return 0


def test_sagemaker(tmpdir):
    assert sagemaker_object_detection(tmpdir) == 0
    assert sagemaker_instance_segmentation(tmpdir) == 0
