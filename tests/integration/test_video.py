import os
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestVideo(BaseTestCase):
    PROJECT_NAME = "test video upload1"
    SECOND_PROJECT_NAME = "test video upload2"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_NAME = "new_folder"
    TEST_VIDEO_FOLDER_PATH = "data_set/sample_videos/single"
    TEST_VIDEO_NAME = "video.mp4"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_VIDEO_FOLDER_PATH)

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
        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 5)
        self.assertEqual(
            len(sa.search_images(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}")),
            len(sa.search_images(self.PROJECT_NAME)),
        )

    def test_single_video_upload(self):
        sa.upload_video_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/{self.TEST_VIDEO_NAME}",
            target_fps=1,
        )
        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 5)

    #  todo check
    # def test_video_deep(self):
    #     with tempfile.TemporaryDirectory() as temp_dir:
    #         logger = logging.getLogger()
    #
    #         controller = Controller(
    #             backend_client=SuperannotateBackendService(
    #                 api_url=constances.BACKEND_URL,
    #                 auth_token=ConfigRepository().get_one("token"),
    #                 logger=logger,
    #             ),
    #             response=Response(),
    #         )
    #         controller.extract_video_frames(
    #             project_name=self.PROJECT_NAME,
    #             folder_name="",
    #             video_path=self.folder_path + "/single/video.mp4",
    #             extract_path=temp_dir,
    #             target_fps=1,
    #             start_time=0.0,
    #             end_time=None,
    #             annotation_status=None,
    #             image_quality_in_editor=None,
    #             limit=10,
    #         )
    #         ground_truth_dir_name = self.folder_path + "/single/ground_truth_frames"
    #         for file_name in os.listdir(temp_dir):
    #             temp_file_path = temp_dir + "/" + file_name
    #             truth_file_path = ground_truth_dir_name + "/" + file_name
    #             img1 = cv2.imread(temp_file_path)
    #             img2 = cv2.imread(truth_file_path)
    #             diff = np.sum(img2 - img1) + np.sum(img2 - img1)
    #             assert diff == 0
