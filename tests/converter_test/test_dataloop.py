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


def test_dataloop_convert_vector(tmpdir):
    project_name = "dataloop2sa_vector_annotation"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'DataLoop' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'DataLoop', '', 'Vector', 'vector_annotation'
    )

    description = 'dataloop vector annotation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_dataloop_convert_object(tmpdir):
    project_name = "dataloop2sa_vector_object"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'DataLoop' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'DataLoop', '', 'Vector', 'object_detection'
    )

    description = 'dataloop object detection'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_dataloop_convert_instance(tmpdir):
    project_name = "dataloop2sa_vector_instance"

    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'DataLoop' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, 'DataLoop', '', 'Vector', 'instance_segmentation'
    )
    description = 'dataloop instance segmentation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)
