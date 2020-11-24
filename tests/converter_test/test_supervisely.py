import superannotate as sa


def supervisely_convert_vector(tmpdir):
    out_dir = tmpdir / 'vector_annotation'
    sa.import_annotation_format(
        'tests/converter_test/Supervisely/input/toSuperAnnotate/vector',
        str(out_dir), 'Supervisely', '', 'Vector', 'vector_annotation', 'Web'
    )

    project_name = "supervisely_test_vector"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)

    return 0


def supervisely_convert_object(tmpdir):
    out_dir = tmpdir / 'object_detection'
    sa.import_annotation_format(
        'tests/converter_test/Supervisely/input/toSuperAnnotate/vector',
        str(out_dir), 'Supervisely', '', 'Vector', 'object_detection', 'Desktop'
    )

    return 0


def supervisely_convert_instance(tmpdir):
    out_dir = tmpdir / 'instance_segmentation'
    sa.import_annotation_format(
        'tests/converter_test/Supervisely/input/toSuperAnnotate/vector',
        str(out_dir), 'Supervisely', '', 'Vector', 'instance_segmentation',
        'Web'
    )

    return 0


def supervisely_convert_keypoint(tmpdir):
    out_dir = tmpdir / 'keypoint_detection'
    sa.import_annotation_format(
        'tests/converter_test/Supervisely/input/toSuperAnnotate/keypoints',
        str(out_dir), 'Supervisely', '', 'Vector', 'keypoint_detection', 'Web'
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

    return 0


def supervisely_convert_instance_pixel(tmpdir):
    out_dir = tmpdir / 'instance_segmentation_pixel'
    sa.import_annotation_format(
        'tests/converter_test/Supervisely/input/toSuperAnnotate/instance',
        str(out_dir), 'Supervisely', '', 'Pixel', 'instance_segmentation', 'Web'
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

    return 0


def test_supervisely(tmpdir):
    assert supervisely_convert_keypoint(tmpdir) == 0
    assert supervisely_convert_instance(tmpdir) == 0
    assert supervisely_convert_object(tmpdir) == 0
    assert supervisely_convert_vector(tmpdir) == 0
    assert supervisely_convert_instance_pixel(tmpdir) == 0
