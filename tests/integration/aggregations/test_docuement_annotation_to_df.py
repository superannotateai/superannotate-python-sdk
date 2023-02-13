import logging
import os
import tempfile
from pathlib import Path
from unittest import mock
from unittest import TestCase

from distutils.dir_util import copy_tree
from src.superannotate import SAClient

sa = SAClient()


class TestAggregateDocumentAnnotation(TestCase):
    PROJECT_TYPE = "Document"
    FOLDER_PATH = "data_set/document_df_data"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.FOLDER_PATH)

    def test_data_filling(self):
        df = sa.aggregate_annotations_as_df(self.folder_path, self.PROJECT_TYPE, None)
        instance_ids = {i for i in df.instanceId if i is not None}
        tag_ids = {i for i in df.tagId if i is not None}

        self.assertEqual(instance_ids, {0, 1})
        self.assertEqual(tag_ids, {0, 1})

    def test_nested_folders_data_filling(self):
        df = sa.aggregate_annotations_as_df(self.folder_path, self.PROJECT_TYPE)
        folder_names = {i for i in df.folderName}

        self.assertEqual(folder_names, {"folder", None})

    def test_nested_folder_data_filling(self):
        df = sa.aggregate_annotations_as_df(
            self.folder_path, self.PROJECT_TYPE, folder_names=["folder"]
        )
        folder_names = {i for i in df.folderName}
        self.assertEqual(folder_names, {"folder"})

    def test_empty_folder_log(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree(f"{self.folder_path}/classes", f"{temp_dir}/classes")
            logger = logging.getLogger("sa")
            with mock.patch.object(logger, "warning") as mock_log:
                _ = sa.aggregate_annotations_as_df(temp_dir, self.PROJECT_TYPE)
                mock_log.assert_called_with(
                    f"Could not find annotations in {temp_dir}."
                )
