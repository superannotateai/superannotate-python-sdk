import json
import os
import time
from pathlib import Path
from typing import List
from unittest import TestCase

from src.superannotate import SAClient

sa = SAClient()


class TestItemAttachCategory(TestCase):
    PROJECT_NAME = "TestItemAttachCategory"
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

    @staticmethod
    def _attach_items(path: str, names: List[str]):
        sa.attach_items(path, [{"name": name, "url": f"url-{name}"} for name in names])

    def test_attache_category(self):
        self._attach_items(self.PROJECT_NAME, ["item-1", "item-2"])
        sa.create_categories(self.PROJECT_NAME, ["category-1", "category-2"])

        with self.assertLogs("sa", level="INFO") as cm:
            sa.set_items_category(self.PROJECT_NAME, ["item-1", "item-2"], "category-1")
            assert (
                "INFO:sa:category-1 category successfully added to 2 items."
                == cm.output[0]
            )

        items = sa.list_items(self.PROJECT_NAME, include=["categories"])
        assert all(i["categories"][0]["value"] == "category-1" for i in items)

        # test get categories to use get_item_by_id
        item = sa.get_item_by_id(
            self._project["id"], items[0]["id"], include=["categories"]
        )
        assert item["categories"][0]["value"] == "category-1"

    def test_remove_items_category(self):
        self._attach_items(self.PROJECT_NAME, ["item-1", "item-2", "item-3"])
        sa.create_categories(self.PROJECT_NAME, ["category-1", "category-2"])
        sa.set_items_category(
            self.PROJECT_NAME, ["item-1", "item-2", "item-3"], "category-1"
        )

        items = sa.list_items(self.PROJECT_NAME, include=["categories"])
        assert len(items) == 3
        assert all(
            len(i["categories"]) == 1 and i["categories"][0]["value"] == "category-1"
            for i in items
        )

        with self.assertLogs("sa", level="INFO") as cm:
            sa.remove_items_category(self.PROJECT_NAME, ["item-1", "item-2"])
            assert "INFO:sa:Category successfully removed from 2 items." == cm.output[0]

        items = sa.list_items(self.PROJECT_NAME, include=["categories"])
        item_dict = {item["name"]: item for item in items}

        assert len(item_dict["item-1"]["categories"]) == 0
        assert len(item_dict["item-2"]["categories"]) == 0

        assert len(item_dict["item-3"]["categories"]) == 1
        assert item_dict["item-3"]["categories"][0]["value"] == "category-1"

    def test_remove_items_category_by_ids(self):
        self._attach_items(self.PROJECT_NAME, ["item-4", "item-5"])
        sa.create_categories(self.PROJECT_NAME, ["category-test"])
        sa.set_items_category(self.PROJECT_NAME, ["item-4", "item-5"], "category-test")

        items = sa.list_items(self.PROJECT_NAME, include=["categories"])
        item_ids = [
            item["id"] for item in items if item["name"] in ["item-4", "item-5"]
        ]

        sa.remove_items_category(self.PROJECT_NAME, item_ids)
        items = sa.list_items(self.PROJECT_NAME, include=["categories"])
        for item in items:
            if item["name"] in ["item-4", "item-5"]:
                assert len(item["categories"]) == 0

    def test_remove_items_category_with_folder(self):
        folder_name = "test-folder"
        sa.create_folder(self.PROJECT_NAME, folder_name)
        folder_path = f"{self.PROJECT_NAME}/{folder_name}"
        self._attach_items(folder_path, ["folder-item-1", "folder-item-2"])

        sa.create_categories(self.PROJECT_NAME, ["folder-category"])
        sa.set_items_category(
            folder_path, ["folder-item-1", "folder-item-2"], "folder-category"
        )

        sa.remove_items_category(folder_path, ["folder-item-1"])

        items = sa.list_items(
            project=self.PROJECT_NAME, folder=folder_name, include=["categories"]
        )
        item_dict = {item["name"]: item for item in items}

        assert len(item_dict["folder-item-1"]["categories"]) == 0
        assert len(item_dict["folder-item-2"]["categories"]) == 1
        assert item_dict["folder-item-2"]["categories"][0]["value"] == "folder-category"
