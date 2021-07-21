import subprocess
import time
from pathlib import Path
import tempfile
import superannotate as sa
from superannotate.db.projects import _extract_frames_from_video
import os
import numpy as np
import cv2 as cv

PROJECT_NAME1 = "test video upload1"
PROJECT_NAME2 = "test video upload2"


def test_video(tmpdir):
    tmpdir = Path(tmpdir)
    projects = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    time.sleep(2)

    project = sa.create_project(PROJECT_NAME1, "test", "Vector")
    print(project)
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
    time.sleep(2)

    project = sa.create_project(PROJECT_NAME2, "test", "Vector")
    time.sleep(2)
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


def test_video_deep():
    tempdir = tempfile.TemporaryDirectory()
    _extract_frames_from_video(
        start_time=0.0,
        end_time=None,
        video_path="./tests/sample_videos/single/video.mp4",
        tempdir=tempdir,
        limit=10,
        target_fps=1
    )
    temp_dir_name = tempdir.name
    ground_truth_dir_name = "./tests/sample_videos/single/ground_truth_frames"
    temp_files = os.listdir(temp_dir_name)
    for file_name in temp_files:
        temp_file_path = temp_dir_name + "/" + file_name
        truth_file_path = ground_truth_dir_name + "/" + file_name
        img1 = cv.imread(temp_file_path)
        img2 = cv.imread(truth_file_path)
        diff = np.sum(img2 - img1) + np.sum(img2 - img1)
        assert diff == 0
