import os
from os.path import dirname

from src.superannotate import SAClient
sa = SAClient()
from src.superannotate.lib.core.plugin import VideoPlugin
from tests.integration.base import BaseTestCase
import pytest


class TestVideo(BaseTestCase):
    PROJECT_NAME = "test video upload1"
    SECOND_PROJECT_NAME = "test video upload2"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_NAME = "new_folder"
    TEST_VIDEO_FOLDER_PATH = "data_set/sample_videos/single"
    TEST_VIDEO_FOLDER_PATH_BIG = "data_set/sample_videos/earth_video"
    TEST_VIDEO_NAME = "video.mp4"
    TEST_FOLDER_NAME_BIG_VIDEO = "big"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_VIDEO_FOLDER_PATH)

    @property
    def folder_path_big(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_VIDEO_FOLDER_PATH_BIG)

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )
        self._second_project = sa.create_project(
            self.SECOND_PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        for project_name in (self.PROJECT_NAME, self.SECOND_PROJECT_NAME):
            projects = sa.search_projects(project_name, return_metadata=True)
            for project in projects:
                sa.delete_project(project)

    def test_video_upload_from_folder(self):
        sa.upload_videos_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, target_fps=1
        )

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        sa.upload_videos_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}",
            self.folder_path,
            target_fps=1,
        )
        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 5)
        self.assertEqual(
            len(sa.search_items(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}")),
            len(sa.search_items(self.PROJECT_NAME)),
        )

    def test_single_video_upload(self):
        sa.upload_video_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/{self.TEST_VIDEO_NAME}",
            target_fps=1,
        )
        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 5)

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def test_video_big(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_BIG_VIDEO)
        sa.upload_video_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_BIG_VIDEO}",
            f"{self.folder_path_big}/earth.mov",
            target_fps=1,
        )
        self.assertEqual(len(sa.search_items(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_BIG_VIDEO}")), 31)
        sa.upload_video_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_BIG_VIDEO}",
            f"{self.folder_path_big}/earth.mov",
            target_fps=1,
        )
        self.assertIn("31 already existing images found that won't be uploaded.", self._caplog.text)

    @pytest.mark.flaky(reruns=2)
    def test_frame_extraction(self):
        frames_gen = VideoPlugin.frames_generator(
            f"{self.folder_path_big}/earth.mov", target_fps=None, start_time=0.0, end_time=None
        )
        self.assertEqual(len([*frames_gen]), 901)
        frames_gen = VideoPlugin.frames_generator(
            f"{self.folder_path_big}/earth.mov", target_fps=None, start_time=10.0, end_time=None
        )
        self.assertGreaterEqual(len([*frames_gen]), 589)
