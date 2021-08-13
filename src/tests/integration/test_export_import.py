import io
import os
import tempfile
import time
from os.path import dirname

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestExportImport(BaseTestCase):
    PROJECT_NAME = "export_import"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_path(self):
        return os.path.join(
            dirname(dirname(__file__)), self.TEST_FOLDER_PATH, "classes/classes.json"
        )

    def test_export_import(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="InProgress",
        )
        time.sleep(2)

        with tempfile.TemporaryDirectory() as tmpdir_name:
            export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)
            sa.download_export(self.PROJECT_NAME, export, tmpdir_name)
            self.assertEqual(len(os.listdir(tmpdir_name)),4)












# from pathlib import Path
# import json
#
# import pytest
#
# import superannotate as sa
#
# from .common import upload_project
#
# sa.init(Path.home() / ".superannotate" / "config.json")
#
# PROJECT_NAME = "test export import"
# PROJECT_FOLDER = Path("./tests/sample_project_vector")
#
#
# def test_basic_export(tmpdir):
#     tmpdir = Path(tmpdir)
#
#     project = upload_project(
#         PROJECT_FOLDER,
#         PROJECT_NAME,
#         't',
#         'Vector',
#         annotation_status='InProgress'
#     )
#     # projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
#     # for pr in projects_found:
#     #     sa.delete_project(pr)
#
#     # project = sa.create_project(PROJECT_NAME, "t", "Vector")
#     # sa.upload_images_from_folder_to_project(
#     #     project, PROJECT_FOLDER, annotation_status="InProgress"
#     # )
#
#     # sa.create_annotation_classes_from_classes_json(
#     #     project, PROJECT_FOLDER / "classes" / "classes.json"
#     # )
#     # sa.upload_annotations_from_folder_to_project(project, PROJECT_FOLDER)
#     len_orig = len(sa.search_images(project))
#
#     export = sa.prepare_export(project, include_fuse=True)
#
#     sa.download_export(project, export, tmpdir)
#
#     projects_found = sa.search_projects(
#         PROJECT_NAME + " import", return_metadata=True
#     )
#     for pr in projects_found:
#         sa.delete_project(pr)
#     project_new = sa.create_project(PROJECT_NAME + " import", "f", "Vector")
#     sa.upload_images_from_folder_to_project(
#         project_new, tmpdir, annotation_status="InProgress"
#     )
#     len_new = len(sa.search_images(project_new))
#
#     assert len_new == len_orig
