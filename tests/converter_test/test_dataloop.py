import superannotate as sa


def dataloop_convert(tmpdir):
    out_dir = tmpdir / 'output'
    sa.import_annotation_format(
        'tests/converter_test/DataLoop/input/toSuperAnnotate', str(out_dir),
        'DataLoop', '', 'Vector', 'vector_annotation', 'Web'
    )
    # project_name = "dataloop_test"

    # projects = sa.search_projects(project_name, True)
    # if projects:
    #     sa.delete_project(projects[0])
    # project = sa.create_project(project_name, "converter vector", "Vector")

    # sa.create_annotation_classes_from_classes_json(
    #     project, out_dir + "/classes/classes.json"
    # )
    # sa.upload_images_from_folder_to_project(project, out_dir)
    # sa.upload_annotations_from_folder_to_project(project, out_dir)
    return 0


def test_dataloop(tmpdir):
    assert dataloop_convert(tmpdir) == 0
