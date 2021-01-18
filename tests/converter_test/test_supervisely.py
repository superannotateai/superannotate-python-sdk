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


def test_supervisely_convert_vector(tmpdir):
    project_name = "supervisely_test_vector_basic"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'vector'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Vector', 'vector_annotation'
    )

    description = 'supervisely vector annotation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_supervisely_convert_object(tmpdir):
    project_name = "supervisely_test_object"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'vector'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Vector', 'object_detection'
    )

    description = 'supervisely object detection'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_supervisely_convert_instance(tmpdir):
    project_name = "supervisely_test_vector_instance"
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'vector'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Vector', 'instance_segmentation'
    )

    description = 'supervisely instance segmentation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_supervisely_convert_keypoint(tmpdir):
    project_name = "supervisely_test_keypoint"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'keypoints'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Vector', 'keypoint_detection'
    )

    description = 'supervisely keypoint'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_supervisely_convert_instance_pixel(tmpdir):
    project_name = "supervisely_test_instance_pixel"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'instance'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Pixel', 'instance_segmentation'
    )

    description = 'supervisely instance segmentation'
    ptype = 'Pixel'
    upload_project(out_dir, project_name, description, ptype)
