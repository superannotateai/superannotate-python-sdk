from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestListFolders(BaseTestCase):
    PROJECT_NAME = "TestListFolders"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_NAME_1 = "folder_1"
    TEST_FOLDER_NAME_2 = "folder_2"
    TEST_FOLDER_NAME_3 = "folder_3"
    TEST_FOLDER_NAME_4 = "test_folder"

    def test_list_folders_name_filters(self):
        """Test all name-based filtering options"""
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_4)

        # Basic listing (3 folders + 1 root)
        folders = sa.list_folders(self.PROJECT_NAME)
        assert len(folders) == 4

        # Exact name
        folders = sa.list_folders(self.PROJECT_NAME, name=self.TEST_FOLDER_NAME_1)
        assert len(folders) == 1
        assert folders[0]["name"] == self.TEST_FOLDER_NAME_1

        # Contains
        folders = sa.list_folders(self.PROJECT_NAME, name__contains="folder_")
        assert len(folders) == 2

        folders = sa.list_folders(self.PROJECT_NAME, name__contains="test")
        assert len(folders) == 1
        assert folders[0]["name"] == self.TEST_FOLDER_NAME_4

        # Starts with
        folders = sa.list_folders(self.PROJECT_NAME, name__starts="folder")
        assert len(folders) == 2

        # Ends with
        folders = sa.list_folders(self.PROJECT_NAME, name__ends="_1")
        assert len(folders) == 1
        assert folders[0]["name"] == self.TEST_FOLDER_NAME_1

        # Name in list
        folders = sa.list_folders(
            self.PROJECT_NAME,
            name__in=[self.TEST_FOLDER_NAME_1, self.TEST_FOLDER_NAME_4],
        )
        assert len(folders) == 2
        folder_names = {folder["name"] for folder in folders}
        assert self.TEST_FOLDER_NAME_1 in folder_names
        assert self.TEST_FOLDER_NAME_4 in folder_names

    def test_list_folders_id_filters(self):
        """Test all ID-based filtering options"""
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_4)

        # Get all folders to extract IDs
        folders = sa.list_folders(self.PROJECT_NAME)
        folder_1 = next(f for f in folders if f["name"] == self.TEST_FOLDER_NAME_1)
        folder_2 = next(f for f in folders if f["name"] == self.TEST_FOLDER_NAME_2)
        folder_4 = next(f for f in folders if f["name"] == self.TEST_FOLDER_NAME_4)

        # Exact folder ID
        folders = sa.list_folders(self.PROJECT_NAME, id=folder_1["id"])
        assert len(folders) == 1
        assert folders[0]["name"] == self.TEST_FOLDER_NAME_1
        assert folders[0]["id"] == folder_1["id"]

        # Folder ID in list
        folders = sa.list_folders(
            self.PROJECT_NAME,
            id__in=[folder_1["id"], folder_4["id"]],
        )
        assert len(folders) == 2
        folder_ids = {folder["id"] for folder in folders}
        assert folder_1["id"] in folder_ids
        assert folder_4["id"] in folder_ids

        # Combined ID and name filter
        folders = sa.list_folders(
            self.PROJECT_NAME,
            id=folder_1["id"],
            name=self.TEST_FOLDER_NAME_1,
        )
        assert len(folders) == 1
        assert folders[0]["name"] == self.TEST_FOLDER_NAME_1
        assert folders[0]["id"] == folder_1["id"]

        # ID with name filter (should return empty if mismatch)
        folders = sa.list_folders(
            self.PROJECT_NAME,
            id=folder_1["id"],
            name=self.TEST_FOLDER_NAME_2,
        )
        assert len(folders) == 0

    def test_list_folders_status_filters(self):
        """Test all status-based filtering options"""
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_3)

        sa.set_folder_status(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2, "InProgress")
        sa.set_folder_status(self.PROJECT_NAME, self.TEST_FOLDER_NAME_3, "Completed")

        # Exact status
        folders = sa.list_folders(self.PROJECT_NAME, status="NotStarted")
        assert len(folders) == 1
        assert folders[0]["name"] == self.TEST_FOLDER_NAME_1

        folders = sa.list_folders(self.PROJECT_NAME, status="InProgress")
        assert len(folders) == 1
        assert folders[0]["name"] == self.TEST_FOLDER_NAME_2

        # Status in list
        folders = sa.list_folders(
            self.PROJECT_NAME, status__in=["NotStarted", "InProgress"]
        )
        assert len(folders) == 2
        folder_names = {folder["name"] for folder in folders}
        assert self.TEST_FOLDER_NAME_1 in folder_names
        assert self.TEST_FOLDER_NAME_2 in folder_names

        # Status not equal
        folders = sa.list_folders(self.PROJECT_NAME, status__ne="NotStarted")
        assert len(folders) == 2

        # Status not in list
        folders = sa.list_folders(
            self.PROJECT_NAME, status__notin=["NotStarted", "OnHold"]
        )
        assert len(folders) == 3  # root folder is also returned
        folder_names = {folder["name"] for folder in folders}
        assert self.TEST_FOLDER_NAME_2 in folder_names
        assert self.TEST_FOLDER_NAME_3 in folder_names

    def test_list_folders_combined_and_edge_cases(self):
        """Test combined filters, metadata structure, and edge cases"""
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)

        sa.set_folder_status(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1, "InProgress")

        # Combined filters
        folders = sa.list_folders(
            self.PROJECT_NAME, name__contains="folder", status="InProgress"
        )
        assert len(folders) == 1
        assert folders[0]["name"] == self.TEST_FOLDER_NAME_1

        # Metadata structure
        folders = sa.list_folders(self.PROJECT_NAME)
        assert len(folders) == 3  # 2 created folders + 1 root
        folder = folders[0]
        assert "id" in folder
        assert "name" in folder
        assert "status" in folder
        assert "project_id" in folder
        assert "team_id" in folder
        assert "is_root" in folder

        # Empty result
        folders = sa.list_folders(self.PROJECT_NAME, name="nonexistent")
        assert len(folders) == 0

        # By project ID
        project = sa.get_project_metadata(self.PROJECT_NAME)
        folders = sa.list_folders(project["id"])
        assert len(folders) == 3  # 2 created folders + 1 root

    def test_list_folders_invalid_filters(self):
        """Test that invalid filters raise appropriate errors"""
        # Invalid filter field
        with self.assertRaisesRegex(AppException, "Invalid filter param provided."):
            sa.list_folders(self.PROJECT_NAME, invalid_field="value")

        # Invalid operator
        with self.assertRaisesRegex(AppException, "Invalid filter param provided."):
            sa.list_folders(self.PROJECT_NAME, name__invalid="value")

        # Invalid status value
        with self.assertRaisesRegex(
            ValueError, "InvalidStatus is not a valid FolderStatus"
        ):
            sa.list_folders(self.PROJECT_NAME, status="InvalidStatus")

        # Invalid status in list
        with self.assertRaisesRegex(
            ValueError, "InvalidStatus is not a valid FolderStatus"
        ):
            sa.list_folders(
                self.PROJECT_NAME, status__in=["NotStarted", "InvalidStatus"]
            )
