from unittest import TestCase

from src.superannotate import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestGenerateItemsMM(TestCase):
    PROJECT_NAME = "TestGenerateItemsMM"
    PROJECT_DESCRIPTION = "TestGenerateItemsMM"
    PROJECT_TYPE = "Multimodal"
    FOLDER_NAME = "test_folder"
    MULTIMODAL_FORM = {
        "components": [
            {
                "id": "r_qx07c6",
                "type": "audio",
                "permissions": [],
                "hasTooltip": False,
                "exclude": False,
                "label": "",
                "value": "",
            }
        ],
        "readme": "",
    }

    def setUp(self, *args, **kwargs):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[{"attribute": "TemplateState", "value": 1}],
            form=self.MULTIMODAL_FORM,
        )

    def tearDown(self) -> None:
        try:
            projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
            for project in projects:
                try:
                    sa.delete_project(project)
                except Exception as e:
                    print(str(e))
        except Exception as e:
            print(str(e))

    def test_generate_items_root(self):
        sa.generate_items(self.PROJECT_NAME, 100, name="a")
        items = sa.list_items(self.PROJECT_NAME)

        assert len(items) == 100

        expected_names = {f"a_{i:05d}" for i in range(1, 101)}
        actual_names = {item["name"] for item in items}

        assert actual_names == expected_names

    def test_generate_items_in_folder(self):
        path = f"{self.PROJECT_NAME}/{self.FOLDER_NAME}"

        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.generate_items(path, 100, name="a")
        items = sa.list_items(project=self.PROJECT_NAME, folder=self.FOLDER_NAME)

        assert len(items) == 100

        expected_names = {f"a_{i:05d}" for i in range(1, 101)}
        actual_names = {item["name"] for item in items}

        assert actual_names == expected_names

    def test_invalid_name(self):
        with self.assertRaisesRegexp(
            AppException,
            "Invalid item name.",
        ):
            sa.generate_items(self.PROJECT_NAME, 100, name="a" * 115)

        with self.assertRaisesRegexp(
            AppException,
            "Invalid item name.",
        ):
            sa.generate_items(self.PROJECT_NAME, 100, name="m<:")

    def test_item_count(self):
        with self.assertRaisesRegexp(
            AppException,
            "The number of items you want to attach exceeds the limit of 50 000 items per folder.",
        ):
            sa.generate_items(self.PROJECT_NAME, 50_001, name="a")
