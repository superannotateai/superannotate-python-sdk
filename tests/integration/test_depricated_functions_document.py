import os
from os.path import dirname
import pytest
from unittest import TestCase

from src.superannotate import SAClient
from src.superannotate import AppException
from src.superannotate.lib.core import LIMITED_FUNCTIONS
from src.superannotate.lib.core import INVALID_PROJECT_TYPE_TO_PROCESS
from src.superannotate.lib.core import ProjectType
from src.superannotate.lib.core import DEPRICATED_DOCUMENT_VIDEO_MESSAGE


sa = SAClient()


class TestDeprecatedFunctionsDocument(TestCase):
    PROJECT_NAME = "TestDeprecatedFunctionsDocument first froject"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"
    PATH_TO_URLS = "data_set/attach_urls.csv"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_FOLDER_VIDEO_EXPORT_PATH = "data_set/sample_video_text_export"
    UPLOAD_IMAGE_NAME = "6022a74b5384c50017c366cv"
    PROJECT_NAME_2 = "TestDeprecatedFunctionsDocument second project"
    PROJECT_DESCRIPTION_2 = "second project"
    PROJECT_TYPE_2 = "Vector"
    EXCEPTION_MESSAGE = LIMITED_FUNCTIONS[ProjectType.DOCUMENT.value]
    EXCEPTION_MESSAGE_2 = INVALID_PROJECT_TYPE_TO_PROCESS
    EXCEPTION_MESSAGE_DOCUMENT_VIDEO = DEPRICATED_DOCUMENT_VIDEO_MESSAGE

    def setUp(self, *args, **kwargs):
        self.tearDown()

        sa.create_project(
            self.PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

        sa.create_project(
            self.PROJECT_NAME_2, self.PROJECT_DESCRIPTION_2, self.PROJECT_TYPE_2
        )

    def tearDown(self) -> None:
        projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
        for project in projects:
            sa.delete_project(project)

        projects = sa.search_projects(self.PROJECT_NAME_2, return_metadata=True)
        for project in projects:
            sa.delete_project(project)

    @property
    def video_export_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_VIDEO_EXPORT_PATH)

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def annotation_path(self):
        return f'{self.folder_path}/example_image_1.jpg___objects.json'

    @property
    def image_path(self):
        return f'{self.folder_path}/example_image_1.jpg'

    @pytest.mark.flaky(reruns=2)
    def test_deprecated_functions(self):
        try:
            sa.upload_images_from_folder_to_project(self.PROJECT_NAME, "some")
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.upload_images_to_project(self.PROJECT_NAME, ["some"])
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.upload_image_annotations(self.PROJECT_NAME, "some", self.annotation_path)
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.download_image_annotations(self.PROJECT_NAME, self.UPLOAD_IMAGE_NAME, "./")
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.copy_image(self.PROJECT_NAME, self.UPLOAD_IMAGE_NAME, self.PROJECT_NAME_2)
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.upload_images_to_project(self.PROJECT_NAME, [self.image_path, ])
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.upload_video_to_project(self.PROJECT_NAME, "some path")
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.get_project_image_count(self.PROJECT_NAME)
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.set_project_workflow(self.PROJECT_NAME, [{}])
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.upload_preannotations_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.add_annotation_point_to_image(self.PROJECT_NAME, self.UPLOAD_IMAGE_NAME, [1, 2], "some class")
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.get_project_workflow(self.PROJECT_NAME)
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.prepare_export(self.PROJECT_NAME, include_fuse=True, only_pinned=True)
        except AppException as e:
            self.assertIn("Include fuse functionality is not supported", str(e))
        try:
            sa.benchmark(self.PROJECT_NAME, "some", ["some folder1"])
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.upload_videos_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE, str(e))
        try:
            sa.set_project_default_image_quality_in_editor(self.PROJECT_NAME,"original")
        except AppException as e:
            self.assertIn(self.EXCEPTION_MESSAGE_DOCUMENT_VIDEO, str(e))
