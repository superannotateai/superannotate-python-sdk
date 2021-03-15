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
        f'superannotatecli create-project --name "{PROJECT_NAME}" --description gg --type Vector',
        check=True,
        shell=True
    )
    project = PROJECT_NAME
    subprocess.run(
        f'superannotatecli create-folder --project "{PROJECT_NAME}" --name folder1',
        check=True,
        shell=True
    )
    sa.create_annotation_classes_from_classes_json(
        PROJECT_NAME, "./tests/sample_recursive_test/classes/classes.json"
    )
    subprocess.run(
        f'superannotatecli upload-images --project "{PROJECT_NAME}" --folder ./tests/sample_recursive_test --extensions=jpg --set-annotation-status QualityCheck',
        check=True,
        shell=True
    )
    time.sleep(1)
    assert len(sa.search_images(project)) == 1
    subprocess.run(
        f'superannotatecli upload-images --project "{PROJECT_NAME}" --folder ./tests/sample_recursive_test --extensions=jpg --recursive',
        check=True,
        shell=True
    )
    time.sleep(1)
    assert len(sa.search_images(project)) == 2

    subprocess.run(
        f'superannotatecli upload-images --project "{PROJECT_NAME}/folder1" --folder ./tests/sample_recursive_test --extensions=jpg --set-annotation-status QualityCheck',
        check=True,
        shell=True
    )
    time.sleep(1)
    assert len(sa.search_images(f"{PROJECT_NAME}/folder1")) == 1

    sa.upload_annotations_from_folder_to_project(
        project, "./tests/sample_recursive_test"
    )
    test_dir1 = tmpdir / "test1"
    test_dir1.mkdir()
    subprocess.run(
        f'superannotatecli export-project --project "{PROJECT_NAME}" --folder {test_dir1}',
        check=True,
        shell=True
    )

    assert len(list(test_dir1.glob("*.json"))) == 1
    assert len(list(test_dir1.glob("*.jpg"))) == 0
    assert len(list(test_dir1.glob("*.png"))) == 0

    test_dir2 = tmpdir / "test2"
    test_dir2.mkdir()
    subprocess.run(
        f'superannotatecli export-project --project "{PROJECT_NAME}" --folder {test_dir2} --include-fuse',
        check=True,
        shell=True
    )

    assert len(list(test_dir2.glob("*.json"))) == 1
    assert len(list(test_dir2.glob("*.jpg"))) == 1
    assert len(list(test_dir2.glob("*.png"))) == 1

    test_dir3 = tmpdir / "test3"
    test_dir3.mkdir()
    subprocess.run(
        f'superannotatecli export-project --project "{PROJECT_NAME}/folder1" --folder {test_dir3}',
        check=True,
        shell=True
    )

    assert len(list(test_dir3.glob("*.json"))) == 0
    assert len(list(test_dir3.glob("*.jpg"))) == 0
    assert len(list(test_dir3.glob("*.png"))) == 0

    assert len(list((test_dir3 / "folder1").glob("*.json"))) == 1
    assert len(list((test_dir3 / "folder1").glob("*.jpg"))) == 0
    assert len(list((test_dir3 / "folder1").glob("*.png"))) == 0
