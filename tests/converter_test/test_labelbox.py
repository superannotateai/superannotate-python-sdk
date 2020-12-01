from pathlib import Path

import superannotate as sa
import os


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

    all_files = os.listdir(out_dir)
    json_files = set(
        [
            file.replace('___objects.json', '')
            for file in all_files if os.path.splitext(file) == '.json'
        ]
    )
    image_files = set(
        [file for file in all_files if os.path.splitext(file) == '.jpg']
    )

    assert json_files == image_files
