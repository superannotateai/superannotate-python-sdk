import os
from os.path import dirname
import tempfile
import time
import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase
import filecmp

class TestImageQuality(BaseTestCase):
    PROJECT_NAME = "img_q"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)


    def test_image_quality_setting1(self):
        sa.upload_images_from_folder_to_project(
            project=self._project["name"], folder_path=self.folder_path
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            sa.download_image(self.PROJECT_NAME, "example_image_1.jpg", tmpdirname + "/", variant="lores")
            assert not filecmp.cmp(
                tmpdirname + "/example_image_1.jpg___lores.jpg",
                self.folder_path + "/example_image_1.jpg",
                shallow=False
            )

    def test_image_quality_setting2(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            sa.set_project_default_image_quality_in_editor(self.PROJECT_NAME, "original")
            time.sleep(2)
            sa.upload_images_from_folder_to_project(
                project=self.PROJECT_NAME, folder_path=self.folder_path
            )
            time.sleep(2)

            sa.download_image(self.PROJECT_NAME, "example_image_1.jpg", tmpdir_name + "/", variant="lores")

            assert filecmp.cmp(
                tmpdir_name + "/example_image_1.jpg___lores.jpg",
                self.folder_path + "/example_image_1.jpg",
                shallow=False
            )















# import time
# from pathlib import Path
# import filecmp
#
# import superannotate as sa
#
# PROJECT_NAME1 = "test image qual setting1"
# PROJECT_NAME2 = "test image qual setting2"
#
#
# def test_image_quality_setting1(tmpdir):
#     tmpdir = Path(tmpdir)
#
#     projects = sa.search_projects(PROJECT_NAME1, return_metadata=True)
#     for project in projects:
#         sa.delete_project(project)
#     time.sleep(2)
#     project = sa.create_project(PROJECT_NAME1, "test", "Vector")
#     time.sleep(2)
#     sa.upload_images_from_folder_to_project(
#         project, "./tests/sample_project_vector"
#     )
#
#     sa.download_image(project, "example_image_1.jpg", tmpdir, variant="lores")
#
#     assert not filecmp.cmp(
#         tmpdir / "example_image_1.jpg___lores.jpg",
#         "./tests/sample_project_vector/example_image_1.jpg",
#         shallow=False
#     )
#
#
# def test_image_quality_setting2(tmpdir):
#     tmpdir = Path(tmpdir)
#
#     projects = sa.search_projects(PROJECT_NAME2, return_metadata=True)
#     for project in projects:
#         sa.delete_project(project)
#     time.sleep(2)
#
#     project = sa.create_project(PROJECT_NAME2, "test", "Vector")
#     time.sleep(2)
#     sa.set_project_default_image_quality_in_editor(project, "original")
#     time.sleep(2)
#     sa.upload_images_from_folder_to_project(
#         project, "./tests/sample_project_vector"
#     )
#     time.sleep(2)
#
#     sa.download_image(project, "example_image_1.jpg", tmpdir, variant="lores")
#
#     assert filecmp.cmp(
#         tmpdir / "example_image_1.jpg___lores.jpg",
#         "./tests/sample_project_vector/example_image_1.jpg",
#         shallow=False
#     )
