from pathlib import Path

import superannotate as sa


def test_dataloop_convert_vector(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'DataLoop' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / 'output_vector'
    sa.import_annotation_format(
        input_dir, out_dir, 'DataLoop', '', 'Vector', 'vector_annotation', 'Web'
    )
    project_name = "dataloop_test_vector"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_dataloop_convert_object(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'DataLoop' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / 'output_object'
    sa.import_annotation_format(
        input_dir, out_dir, 'DataLoop', '', 'Vector', 'object_detection',
        'Desktop'
    )


def test_dataloop_convert_instance(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'DataLoop' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / 'output_instance'
    sa.import_annotation_format(
        input_dir, out_dir, 'DataLoop', '', 'Vector', 'instance_segmentation',
        'Web'
    )
    project_name = "dataloop_test_instance"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)
