from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase
from tests.integration.folders import FOLDER_KEYS

sa = SAClient()


class TestSearchFolders(BaseTestCase):
    PROJECT_NAME = "test TestSearchFolders"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    SPECIAL_CHARS = r"/\:*?“<>|"
    TEST_FOLDER_NAME_1 = "folder_1"
    TEST_FOLDER_NAME_2 = "folder_2"
    TEST_FOLDER_NAME_3 = "folder_3"

    def test_search_folders(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        folders = sa.search_folders(self.PROJECT_NAME)
        assert all(["is_root" not in folder for folder in folders])
        assert len(folders) == 2
        #  with metadata
        folders = sa.search_folders(self.PROJECT_NAME, return_metadata=True)
        for folder in folders:
            self.assertListEqual(list(folder.keys()), FOLDER_KEYS)

        # with status
        folders = sa.search_folders(self.PROJECT_NAME, status="NotStarted")
        assert len(folders) == 2

        # with status list
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_3)
        sa.set_folder_status(
            self.PROJECT_NAME, self.TEST_FOLDER_NAME_3, status="InProgress"
        )
        folders_2 = sa.search_folders(
            self.PROJECT_NAME, status=["NotStarted", "InProgress", "Completed"]
        )
        assert len(folders_2) == 3

        folders_3 = sa.search_folders(
            self.PROJECT_NAME, status=["InProgress", "Completed"]
        )
        assert len(folders_3) == 1

        folders_4 = sa.search_folders(
            self.PROJECT_NAME, status=["NotStarted", "Completed"]
        )
        assert len(folders_4) == 2

        # with invalid status
        pattern = (
            r"(\s+)status(\s+)Available values are 'NotStarted', "
            r"'InProgress', 'Completed', 'OnHold'.(\s+)value is not a valid list"
        )
        with self.assertRaisesRegexp(AppException, pattern):
            folders = sa.search_folders(self.PROJECT_NAME, status="dummy")  # noqa
