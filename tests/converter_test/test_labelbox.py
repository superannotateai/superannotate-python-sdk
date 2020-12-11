from pathlib import Path

import superannotate as sa


def test_labelbox_convert_vector(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'LabelBox' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / "output_vector"
    dataset_name = 'labelbox_example'
    sa.import_annotation(
        input_dir, out_dir, 'LabelBox', dataset_name, 'Vector',
        'vector_annotation', 'Web'
    )

    project_name = "labelbox_vector"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_labelbox_convert_object(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'LabelBox' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / "output_object"
    dataset_name = 'labelbox_example'
    sa.import_annotation(
        input_dir, out_dir, 'LabelBox', dataset_name, 'Vector',
        'object_detection', 'Web'
    )

    project_name = "labelbox_object"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_labelbox_convert_instance(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'LabelBox' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / "output_insance"
    dataset_name = 'labelbox_example'
    sa.import_annotation(
        input_dir, out_dir, 'LabelBox', dataset_name, 'Vector',
        'instance_segmentation', 'Desktop'
    )


def test_labelbox_convert_instance_pixel(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'LabelBox' / 'instance_segmentation' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / "output_insance_pixel"
    dataset_name = 'labelbox_example'
    sa.import_annotation(
        input_dir, out_dir, 'LabelBox', dataset_name, 'Pixel',
        'instance_segmentation', 'Web'
    )

    project_name = "labelbox_instance"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Pixel")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)
