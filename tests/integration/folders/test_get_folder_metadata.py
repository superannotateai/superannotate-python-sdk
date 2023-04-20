from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase
from tests.integration.folders import FOLDER_KEYS

sa = SAClient()


class TestGetFolderMetadata(BaseTestCase):
    PROJECT_NAME = "test TestGetFolderMetadata"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    SPECIAL_CHARS = r"/\:*?“<>|"
    TEST_FOLDER_NAME = "folder_"

    def test_get_folder_metadata(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        folder_metadata = sa.get_folder_metadata(
            self.PROJECT_NAME, self.TEST_FOLDER_NAME
        )
        assert "is_root" not in folder_metadata
        self.assertListEqual(list(folder_metadata.keys()), FOLDER_KEYS)

        # get not exiting folder
        with self.assertRaises(AppException) as cm:
            sa.get_folder_metadata(self.PROJECT_NAME, "dummy folder")
        assert str(cm.exception) == "Folder not found."
