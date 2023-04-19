from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase


sa = SAClient()


class TestDeleteFolders(BaseTestCase):
    PROJECT_NAME = "test TestDeleteFolders"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    SPECIAL_CHARS = r"/\:*?“<>|"
    TEST_FOLDER_NAME_1 = "folder_1"
    TEST_FOLDER_NAME_2 = "folder_2"

    def test_search_folders(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        sa.delete_folders(self.PROJECT_NAME, folder_names=[self.TEST_FOLDER_NAME_1])
        folders = sa.search_folders(self.PROJECT_NAME)
        assert len(folders) == 1

        sa.delete_folders(self.PROJECT_NAME, folder_names=[self.TEST_FOLDER_NAME_2])
        folders = sa.search_folders(self.PROJECT_NAME)
        assert len(folders) == 0

        # test delete multiple
        folder_names = [f"folder_{i}" for i in range(5)]
        [
            sa.create_folder(self.PROJECT_NAME, folder_name)
            for folder_name in folder_names
        ]

        with self.assertRaisesRegexp(AppException, "There is no folder to delete."):
            sa.delete_folders(self.PROJECT_NAME, [])
        pattern = r"(\s+)folder_names(\s+)none is not an allowed value"

        with self.assertRaisesRegexp(AppException, pattern):
            sa.delete_folders(self.PROJECT_NAME, None)  # noqa

        sa.delete_folders(self.PROJECT_NAME, folder_names)
        folders = sa.search_folders(self.PROJECT_NAME)
        assert len(folders) == 0
