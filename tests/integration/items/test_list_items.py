import json
import os
import random
import string
from pathlib import Path

from src.superannotate import AppException
from src.superannotate import SAClient
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestListItems(BaseTestCase):
    PROJECT_NAME = "TestListItems"
    PROJECT_DESCRIPTION = "TestSearchItems"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE1_NAME = "example_image_1.jpg"
    IMAGE2_NAME = "example_image_2.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_list_items(self):
        sa.attach_items(
            self.PROJECT_NAME, [{"name": str(i), "url": str(i)} for i in range(100)]
        )
        sa.set_approval_statuses(self.PROJECT_NAME, "Disapproved")
        items = sa.list_items(self.PROJECT_NAME, approval_status="Disapproved")
        assert len(items) == 100
        items = sa.list_items(self.PROJECT_NAME, approval_status="Approved")
        assert len(items) == 0
        items = sa.list_items(self.PROJECT_NAME, approval_status__in=["Approved", None])
        assert len(items) == 0
        items = sa.list_items(
            self.PROJECT_NAME, approval_status__in=["Disapproved", None]
        )
        assert len(items) == 100

    def test_invalid_filter(self):
        with self.assertRaisesRegexp(
            AppException, "Invalid assignments role provided."
        ):
            sa.list_items(self.PROJECT_NAME, assignments__user_role__in=["Approved"])
        with self.assertRaisesRegexp(
            AppException, "Invalid assignments role provided."
        ):
            sa.list_items(self.PROJECT_NAME, assignments__user_role="Dummy")
        with self.assertRaisesRegexp(AppException, "Invalid status provided."):
            sa.list_items(self.PROJECT_NAME, annotation_status="Dummy")

    def test_list_items_URL_limit(self):
        items_for_attache = []
        item_names = []
        for i in range(125):
            name = f"{''.join(random.choice(string.ascii_letters + string.digits) for _ in range(120))}"
            item_names.append(name)
            items_for_attache.append({"name": name, "url": f"{name}-{i}"})

        sa.attach_items(self.PROJECT_NAME, items_for_attache)
        items = sa.list_items(self.PROJECT_NAME, name__in=item_names)
        assert len(items) == 125


class TestListItemsMultimodal(BaseTestCase):
    PROJECT_NAME = "TestListItemsMultimodal"
    PROJECT_DESCRIPTION = "TestSearchItems"
    PROJECT_TYPE = "Multimodal"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    CATEGORIES = ["c_1", "c_2", "c_3"]
    ANNOTATIONS = [
        {"metadata": {"name": "item_1", "item_category": "c1"}, "data": {}},
        {"metadata": {"name": "item_2", "item_category": "c2"}, "data": {}},
        {"metadata": {"name": "item_3", "item_category": "c3"}, "data": {}},
    ]
    CLASSES_TEMPLATE_PATH = DATA_SET_PATH / "editor_templates/form1_classes.json"
    EDITOR_TEMPLATE_PATH = DATA_SET_PATH / "editor_templates/form1.json"

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            "Multimodal",
            settings=[
                {"attribute": "CategorizeItems", "value": 1},
                {"attribute": "TemplateState", "value": 1},
            ],
        )
        project = sa.controller.get_project(self.PROJECT_NAME)
        with open(self.EDITOR_TEMPLATE_PATH) as f:
            res = sa.controller.service_provider.projects.attach_editor_template(
                sa.controller.team, project, template=json.load(f)
            )
            assert res.ok
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.CLASSES_TEMPLATE_PATH
        )

    def test_list_category_filter(self):
        sa.upload_annotations(
            self.PROJECT_NAME, self.ANNOTATIONS, data_spec="multimodal"
        )
        items = sa.list_items(
            self.PROJECT_NAME,
            include=["categories"],
            categories__value__in=["c1", "c2"],
        )
        assert sorted([i["categories"][0]["value"] for i in items]) == sorted(
            ["c1", "c2"]
        )
        assert (
            len(
                sa.list_items(
                    self.PROJECT_NAME,
                    include=["categories"],
                    categories__value__in=["c3"],
                )
            )
            == 1
        )
