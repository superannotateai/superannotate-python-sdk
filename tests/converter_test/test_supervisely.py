from pathlib import Path

import superannotate as sa


def test_supervisely_convert_vector(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'vector'
    out_dir = Path(tmpdir) / 'vector_annotation'
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Vector', 'vector_annotation',
        'Web'
    )

    project_name = "supervisely_test_vector"

    projects = sa.search_projects(project_name, True)
    for project in projects:
        sa.delete_project(project)
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_supervisely_convert_object(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'vector'
    out_dir = Path(tmpdir) / 'object_detection_desktop'
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Vector', 'object_detection',
        'Desktop'
    )


def test_supervisely_convert_instance(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'vector'
    out_dir = Path(tmpdir) / 'instance_segmentation'
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Vector',
        'instance_segmentation', 'Web'
    )
    project_name = "supervisely_test_vector_convert_instance"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_supervisely_convert_keypoint(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'keypoints'
    out_dir = Path(tmpdir) / 'keypoint_detection'
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Vector', 'keypoint_detection',
        'Web'
    )

    project_name = "supervisely_test_keypoint"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_supervisely_convert_instance_pixel(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'Supervisely' / 'input' / 'toSuperAnnotate' / 'instance'
    out_dir = Path(tmpdir) / 'instance_segmentation_pixel'
    sa.import_annotation(
        input_dir, out_dir, 'Supervisely', '', 'Pixel', 'instance_segmentation',
        'Web'
    )

    project_name = "supervisely_test_instance_pixel"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Pixel")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)
