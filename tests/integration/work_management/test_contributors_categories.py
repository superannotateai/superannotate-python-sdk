import json
import os
import time
from pathlib import Path
from unittest import TestCase

from lib.core.exceptions import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestContributorsCategories(TestCase):
    PROJECT_NAME = "TestContributorsCategories"
    PROJECT_TYPE = "Multimodal"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    EDITOR_TEMPLATE_PATH = os.path.join(
        Path(__file__).parent.parent.parent,
        "data_set/editor_templates/form1.json",
    )
    CLASSES_TEMPLATE_PATH = os.path.join(
        Path(__file__).parent.parent.parent,
        "data_set/editor_templates/form1_classes.json",
    )

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME,
            cls.PROJECT_DESCRIPTION,
            cls.PROJECT_TYPE,
            settings=[
                {"attribute": "TemplateState", "value": 1},
                {"attribute": "CategorizeItems", "value": 2},
            ],
        )
        team = sa.controller.team
        project = sa.controller.get_project(cls.PROJECT_NAME)
        time.sleep(2)

        with open(cls.EDITOR_TEMPLATE_PATH) as f:
            template_data = json.load(f)
            res = sa.controller.service_provider.projects.attach_editor_template(
                team, project, template=template_data
            )
            assert res.ok
        sa.create_annotation_classes_from_classes_json(
            cls.PROJECT_NAME, cls.CLASSES_TEMPLATE_PATH
        )
        users = sa.list_users()
        scapegoat = [
            u for u in users if u["role"] == "Contributor" and u["state"] == "Confirmed"
        ][0]
        cls.scapegoat = scapegoat
        sa.add_contributors_to_project(
            cls.PROJECT_NAME, [scapegoat["email"]], "Annotator"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        projects = sa.search_projects(cls.PROJECT_NAME, return_metadata=True)
        for project in projects:
            try:
                sa.delete_project(project)
            except Exception:
                pass

    def tearDown(self):
        # cleanup categories
        sa.remove_contributors_categories(
            project=self.PROJECT_NAME,
            contributors=[self.scapegoat["email"]],
            categories="*",
        )
        sa.remove_categories(project=self.PROJECT_NAME, categories="*")

    def test_set_contributors_categories(self):
        test_categories = ["Category_A", "Category_B", "Category_C"]
        sa.create_categories(project=self.PROJECT_NAME, categories=test_categories)

        categories = sa.list_categories(project=self.PROJECT_NAME)
        assert len(categories) == len(test_categories)

        with self.assertLogs("sa", level="INFO") as cm:
            sa.set_contributors_categories(
                project=self.PROJECT_NAME,
                contributors=[self.scapegoat["email"]],
                categories=["Category_A", "Category_B"],
            )
            assert (
                "INFO:sa:2 categories successfully added to 1 contributors."
                == cm.output[0]
            )

        project_users = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
            include=["categories"],
        )
        assert len(project_users) == 1
        assert len(project_users[0]["categories"]) == 2
        assert project_users[0]["categories"][0]["name"] == "Category_A"
        assert project_users[0]["categories"][1]["name"] == "Category_B"

    def test_set_contributors_categories_all(self):
        test_categories = ["Category_A", "Category_B", "Category_C", "Category_D"]
        sa.create_categories(project=self.PROJECT_NAME, categories=test_categories)

        categories = sa.list_categories(project=self.PROJECT_NAME)
        assert len(categories) == len(test_categories)

        with self.assertLogs("sa", level="INFO") as cm:
            sa.set_contributors_categories(
                project=self.PROJECT_NAME,
                contributors=[self.scapegoat["email"]],
                categories="*",
            )
            assert (
                "INFO:sa:4 categories successfully added to 1 contributors."
                == cm.output[0]
            )

        project_users = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
            include=["categories"],
        )
        assert len(project_users) == 1
        assert len(project_users[0]["categories"]) == 4
        assert project_users[0]["categories"][0]["name"] == "Category_A"
        assert project_users[0]["categories"][1]["name"] == "Category_B"
        assert project_users[0]["categories"][2]["name"] == "Category_C"
        assert project_users[0]["categories"][3]["name"] == "Category_D"

    def test_set_contributors_categories_by_id(self):
        # Test assigning categories using contributor ID
        test_categories = ["ID_Cat_A", "ID_Cat_B"]
        sa.create_categories(project=self.PROJECT_NAME, categories=test_categories)

        scapegoat_project_id = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
        )[0]["id"]

        sa.set_contributors_categories(
            project=self.PROJECT_NAME,
            contributors=[scapegoat_project_id],
            categories=test_categories,
        )

        # Verify categories were assigned
        project_users = sa.list_users(
            project=self.PROJECT_NAME, id=scapegoat_project_id, include=["categories"]
        )
        assigned_categories = [cat["name"] for cat in project_users[0]["categories"]]
        for category in test_categories:
            assert category in assigned_categories

    def test_set_contributors_categories_nonexistent(self):
        sa.set_contributors_categories(
            project=self.PROJECT_NAME,
            contributors=[self.scapegoat["email"]],
            categories=["NonExistentCategory"],
        )

    def test_remove_contributors_categories(self):
        test_categories = ["RemoveCat_A", "RemoveCat_B", "RemoveCat_C"]
        sa.create_categories(project=self.PROJECT_NAME, categories=test_categories)

        sa.set_contributors_categories(
            project=self.PROJECT_NAME,
            contributors=[self.scapegoat["email"]],
            categories=test_categories,
        )

        project_users = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
            include=["categories"],
        )
        assert len(project_users) == 1
        assert len(project_users[0]["categories"]) == 3

        with self.assertLogs("sa", level="INFO") as cm:
            sa.remove_contributors_categories(
                project=self.PROJECT_NAME,
                contributors=[self.scapegoat["email"]],
                categories=["RemoveCat_A", "RemoveCat_B"],
            )
            assert "INFO:sa:2 categories successfully removed" in cm.output[0]

        project_users = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
            include=["categories"],
        )
        assert len(project_users) == 1
        assert len(project_users[0]["categories"]) == 1
        assert project_users[0]["categories"][0]["name"] == "RemoveCat_C"

    def test_remove_all_contributors_categories(self):
        test_categories = ["AllRemove_X", "AllRemove_Y", "AllRemove_Z"]
        sa.create_categories(project=self.PROJECT_NAME, categories=test_categories)

        # First assign all categories
        sa.set_contributors_categories(
            project=self.PROJECT_NAME,
            contributors=[self.scapegoat["email"]],
            categories=test_categories,
        )

        project_users = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
            include=["categories"],
        )
        assert len(project_users) == 1
        assert len(project_users[0]["categories"]) == 3

        with self.assertLogs("sa", level="INFO") as cm:
            sa.remove_contributors_categories(
                project=self.PROJECT_NAME,
                contributors=[self.scapegoat["email"]],
                categories="*",
            )
            assert "INFO:sa:3 categories successfully removed" in cm.output[0]

        project_users = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
            include=["categories"],
        )
        assert len(project_users) == 1
        assert len(project_users[0]["categories"]) == 0

    def test_set_categories_with_invalid_contributor(self):
        test_categories = ["Category_A", "Category_B", "Category_C"]
        sa.create_categories(project=self.PROJECT_NAME, categories=test_categories)

        with self.assertRaisesRegexp(AppException, "Contributors not found.") as cm:
            sa.set_contributors_categories(
                project=self.PROJECT_NAME,
                contributors=[self.scapegoat["email"], "invalid_email@mail.com"],
                categories=["Category_A", "Category_B"],
            )

    def test_set_contributors_with_invalid_categories(self):
        test_categories = ["Category_A", "Category_B", "Category_C"]
        sa.create_categories(project=self.PROJECT_NAME, categories=test_categories)

        sa.set_contributors_categories(
            project=self.PROJECT_NAME,
            contributors=[self.scapegoat["email"]],
            categories=[
                "Category_A",
                "Category_C",
                "InvalidCategory_1",
                "InvalidCategory_2",
            ],
        )

        project_users = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
            include=["categories"],
        )
        assert len(project_users) == 1
        assert len(project_users[0]["categories"]) == 2
        assert project_users[0]["categories"][0]["name"] == "Category_A"
        assert project_users[0]["categories"][1]["name"] == "Category_C"
