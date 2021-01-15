from pathlib import Path
import superannotate as sa


def upload_project(project_path, project_name, description, ptype):
    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, description, ptype)

    sa.create_annotation_classes_from_classes_json(
        project, project_path / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, project_path)
    sa.upload_annotations_from_folder_to_project(project, project_path)


def test_sagemaker_instance_segmentation(tmpdir):
    project_name = "sagemaker_instance_vector"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'SageMaker' / 'input' / 'toSuperAnnotate' / 'instance_segmentation'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'SageMaker', 'test-obj-detect', 'Pixel',
        'instance_segmentation'
    )

    description = 'sagemaker vector instance segmentation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_sagemaker_object_detection(tmpdir):
    project_name = "sagemaker_object_vector"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'SageMaker' / 'input' / 'toSuperAnnotate' / 'object_detection'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'SageMaker', 'test-obj-detect', 'Vector',
        'object_detection'
    )

    description = 'sagemaker object detection'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)
