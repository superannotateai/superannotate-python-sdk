from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestCreateFolder(BaseTestCase):
    PROJECT_NAME = "test TestCreateFolder"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    SPECIAL_CHARS = r"/\:*?“<>|"
    TEST_FOLDER_NAME = "folder_"

    def test_create_long_name(self):
        err_msg = "The folder name is too long. The maximum length for this field is 80 characters."
        with self.assertRaisesRegexp(AppException, err_msg):
            sa.create_folder(
                self.PROJECT_NAME,
                "A while back I needed to count the amount of letters that "
                "a piece of text in an email template had (to avoid passing any)",
            )

    def test_create_folder_with_special_chars(self):
        sa.create_folder(self.PROJECT_NAME, self.SPECIAL_CHARS)
        folder = sa.get_folder_metadata(
            self.PROJECT_NAME, "_" * len(self.SPECIAL_CHARS)
        )
        self.assertIsNotNone(folder)
        assert "completedCount" not in folder.keys()
        assert "is_root" not in folder.keys()
