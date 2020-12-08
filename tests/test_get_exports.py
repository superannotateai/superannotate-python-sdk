from pathlib import Path

import superannotate as sa

PROJECT_NAME1 = "test_get_exports1"


def test_get_exports(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)
    project = sa.create_project(PROJECT_NAME1, "gg", "Vector")
    sa.upload_images_from_folder_to_project(
        project,
        "./tests/sample_project_vector/",
        annotation_status="QualityCheck"
    )
    sa.create_annotation_classes_from_classes_json(
        project,
        "./tests/sample_project_vector/classes/classes.json",
    )
    sa.upload_annotations_from_folder_to_project(
        project,
        "./tests/sample_project_vector/",
    )
    exports_old = sa.get_exports(project)

    export = sa.prepare_export(project)
    sa.download_export(project, export["name"], tmpdir)
    js = list(tmpdir.glob("*.json"))

    assert len(js) == 4

    exports_new = sa.get_exports(project)

    assert len(exports_new) == len(exports_old) + 1
