from pathlib import Path
import subprocess

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test_cli_image_upload"


def test_cli_image_upload(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)
    project = sa.create_project(PROJECT_NAME, "gg", "Vector")
    subprocess.run(
        [
            f"superannotate image-upload --project '{PROJECT_NAME}' --folder ./tests/sample_recursive_test --extensions=jpg"
        ],
        check=True,
        shell=True
    )
    assert len(sa.search_images(project)) == 1
    subprocess.run(
        [
            f"superannotate image-upload --project '{PROJECT_NAME}' --folder ./tests/sample_recursive_test --extensions=jpg --recursive"
        ],
        check=True,
        shell=True
    )
    assert len(sa.search_images(project)) == 2
