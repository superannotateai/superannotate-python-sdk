import json
import os
import time
from pathlib import Path
from unittest import TestCase

from lib.core.exceptions import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestProjectCategories(TestCase):
    PROJECT_NAME = "TestProjectCategories"
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

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME,
            cls.PROJECT_DESCRIPTION,
            cls.PROJECT_TYPE,
            settings=[
                {"attribute": "TemplateState", "value": 1},
                {"attribute": "CategorizeItems", "value": 1},
            ],
            form=cls.MULTIMODAL_FORM,
        )
        team = sa.controller.team
        project = sa.controller.get_project(cls.PROJECT_NAME)
        time.sleep(5)

        with open(cls.EDITOR_TEMPLATE_PATH) as f:
            template_data = json.load(f)
            res = sa.controller.service_provider.projects.attach_editor_template(
                team, project, template=template_data
            )
            assert res.ok
        sa.create_annotation_classes_from_classes_json(
            cls.PROJECT_NAME, cls.CLASSES_TEMPLATE_PATH
        )

    @classmethod
    def tearDownClass(cls) -> None:
        # cleanup test scores and project
        projects = sa.search_projects(cls.PROJECT_NAME, return_metadata=True)
        for project in projects:
            try:
                sa.delete_project(project)
            except Exception:
                pass

    def test_project_categories_flow(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.create_categories(
                project=self.PROJECT_NAME,
                categories=["SDK_test_category_1", "SDK_test_category_2"],
            )
            assert (
                "INFO:sa:2 categories successfully added to the project."
                == cm.output[0]
            )
        categories = sa.list_categories(project=self.PROJECT_NAME)
        assert len(categories) == 2
        assert categories[0]["name"] == "SDK_test_category_1"
        assert categories[1]["name"] == "SDK_test_category_2"

        # Check that each category has the expected keys
        for category in categories:
            assert "id" in category
            assert "project_id" in category
            assert "createdAt" in category
            assert "updatedAt" in category

        # delete categories
        with self.assertLogs("sa", level="INFO") as cm:
            sa.remove_categories(project=self.PROJECT_NAME, categories="*")
            assert (
                "INFO:sa:2 categories successfully removed from the project."
                == cm.output[0]
            )
        categories = sa.list_categories(project=self.PROJECT_NAME)
        assert not categories

    def test_duplicate_categories_handling(self):
        sa.create_categories(
            project=self.PROJECT_NAME,
            categories=[
                "Category_A",
                "Category_B",
                "category_a",
                "Category_B",
                "Category_A",
            ],
        )
        # Verify only unique categories were created
        categories = sa.list_categories(project=self.PROJECT_NAME)
        category_names = [category["name"] for category in categories]

        # Should only have two categories (first occurrences of each unique name)
        assert len(categories) == 2, f"Expected 2 categories, got {len(categories)}"
        assert (
            "Category_A" in category_names
        ), "Category_A not found in created categories"
        assert (
            "Category_B" in category_names
        ), "Category_B not found in created categories"
        assert (
            "category_a" not in category_names
        ), "Duplicate category_a should not be created"
        # Clean up
        sa.remove_categories(project=self.PROJECT_NAME, categories="*")

    def test_category_name_length_limitation(self):
        long_name = "A" * 250  # 250 characters
        expected_truncated_length = 200  # Expected length after truncation

        # Create the category with the long name
        sa.create_categories(project=self.PROJECT_NAME, categories=[long_name])

        categories = sa.list_categories(project=self.PROJECT_NAME)
        assert len(categories) == 1, "Expected 1 category to be created"

        created_category = categories[0]
        assert len(created_category["name"]) == expected_truncated_length
        assert created_category["name"] == long_name[:expected_truncated_length]
        # Clean up
        sa.remove_categories(project=self.PROJECT_NAME, categories="*")

    def test_delete_all_categories_with_asterisk(self):
        sa.create_categories(
            project=self.PROJECT_NAME, categories=["Cat1", "Cat2", "Cat3"]
        )
        categories = sa.list_categories(project=self.PROJECT_NAME)
        assert len(categories) == 3
        sa.remove_categories(project=self.PROJECT_NAME, categories="*")
        categories = sa.list_categories(project=self.PROJECT_NAME)
        assert len(categories) == 0

    def test_delete_categories_with_empty_list(self):
        with self.assertRaisesRegexp(
            AppException, "Categories should be a list of strings or '*'"
        ):
            sa.remove_categories(project=self.PROJECT_NAME, categories=[])

    def test_delete_invalid_categories(self):
        # silent skip
        sa.remove_categories(
            project=self.PROJECT_NAME,
            categories=["invalid_category_1", "invalid_category_2"],
        )

    def test_create_categories_with_empty_categories(self):
        with self.assertRaisesRegexp(
            AppException, "Categories should be a list of strings."
        ):
            sa.create_categories(project=self.PROJECT_NAME, categories=[])
