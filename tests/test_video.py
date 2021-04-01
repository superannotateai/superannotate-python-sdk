import subprocess
import time
from pathlib import Path

import pytest

import superannotate as sa

PROJECT_NAME1 = "test video upload1"
PROJECT_NAME2 = "test video upload2"


def test_video(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME1, "test", "Vector")
    time.sleep(1)
    sa.create_annotation_class(project, "fr", "#FFAAAA")
    time.sleep(1)
    sa.create_annotation_class(project, "fr2", "#FFAACC")

    sa.upload_videos_from_folder_to_project(
        project, "./tests/sample_videos", target_fps=2
    )

    projects = sa.search_projects(PROJECT_NAME2, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME2, "test", "Vector")

    subprocess.run(
        f'superannotatecli upload-videos --project "{PROJECT_NAME2}" --folder ./tests/sample_videos --target-fps 2',
        check=True,
        shell=True
    )
    time.sleep(5)
    sa.create_annotation_class(project, "fr2", "#FFAACC")

    assert len(sa.search_images(PROJECT_NAME1)) == len(
        sa.search_images(PROJECT_NAME2)
    )

    sa.create_folder(project, "new folder")

    sa.upload_videos_from_folder_to_project(
        PROJECT_NAME2 + "/new folder", "./tests/sample_videos", target_fps=2
    )

    assert len(sa.search_images(PROJECT_NAME2 + "/new folder")) == len(
        sa.search_images(PROJECT_NAME2)
    )