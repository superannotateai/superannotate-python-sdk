from pathlib import Path
import superannotate as sa


def test_sagemaker_instance_segmentation(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'SageMaker' / 'input' / 'toSuperAnnotate' / 'instance_segmentation'
    out_dir = Path(tmpdir) / "instance_segmentation"
    sa.import_annotation_format(
        input_dir, out_dir, 'SageMaker', 'test-obj-detect', 'Pixel',
        'instance_segmentation', 'Web'
    )

    project_name = "sagemaker_instance_segmentation"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Pixel")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_sagemaker_object_detection(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'SageMaker' / 'input' / 'toSuperAnnotate' / 'object_detection'
    out_dir = Path(tmpdir) / "object_detection"
    sa.import_annotation_format(
        input_dir, out_dir, 'SageMaker', 'test-obj-detect', 'Vector',
        'object_detection', 'Desktop'
    )
