from pathlib import Path
import filecmp
import subprocess
import time

import superannotate as sa

import pytest

PROJECT_NAME1 = "test video upload1"
PROJECT_NAME2 = "test video upload2"


def test_image_quality_setting1(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME1, "test", "Vector")

    sa.upload_videos_from_folder_to_project(
        project, "./tests/sample_videos", target_fps=2
    )

    projects = sa.search_projects(PROJECT_NAME2, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project2 = sa.create_project(PROJECT_NAME2, "test", "Vector")

    subprocess.run(
        [
            f'superannotate upload-videos --project "{PROJECT_NAME2}" --folder ./tests/sample_videos --target-fps 2'
        ],
        check=True,
        shell=True
    )
    time.sleep(5)

    assert len(sa.search_images(PROJECT_NAME1)) == len(
        sa.search_images(PROJECT_NAME2)
    )
