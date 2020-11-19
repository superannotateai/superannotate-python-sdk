from pathlib import Path
import subprocess
import time

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test_cli_image_upload"


def test_cli_image_upload_project_export(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)
    subprocess.run(
        f'superannotate create-project --name "{PROJECT_NAME}" --description gg --type Vector',
        check=True,
        shell=True
    )
    project = PROJECT_NAME
    sa.create_annotation_classes_from_classes_json(
        PROJECT_NAME, "./tests/sample_recursive_test/classes/classes.json"
    )
    subprocess.run(
        f'superannotate upload-images --project "{PROJECT_NAME}" --folder ./tests/sample_recursive_test --extensions=jpg --set-annotation-status QualityCheck'
        ,
        check=True,
        shell=True
    )
    time.sleep(1)
    assert len(sa.search_images(project)) == 1
    subprocess.run(
        f'superannotate upload-images --project "{PROJECT_NAME}" --folder ./tests/sample_recursive_test --extensions=jpg --recursive'
        ,
        check=True,
        shell=True
    )
    time.sleep(1)
    assert len(sa.search_images(project)) == 2

    sa.upload_annotations_from_folder_to_project(
        project, "./tests/sample_recursive_test"
    )
    subprocess.run(
        f'superannotate export-project --project "{PROJECT_NAME}" --folder {tmpdir}'
        ,
        check=True,
        shell=True
    )

    assert len(list(tmpdir.glob("*.json"))) == 1
    assert len(list(tmpdir.glob("*.jpg"))) == 0
    assert len(list(tmpdir.glob("*.png"))) == 0
    time.sleep(60)

    subprocess.run(
        f'superannotate export-project --project "{PROJECT_NAME}" --folder {tmpdir} --include-fuse'
        ,
        check=True,
        shell=True
    )

    assert len(list(tmpdir.glob("*.json"))) == 1
    assert len(list(tmpdir.glob("*.jpg"))) == 1
    assert len(list(tmpdir.glob("*.png"))) == 1
