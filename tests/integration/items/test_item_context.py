import json
import os
from pathlib import Path

from src.superannotate import FileChangedError
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestMultimodalProjectBasic(BaseTestCase):
    PROJECT_NAME = "TestMultimodalItemContext"
    PROJECT_TYPE = "Multimodal"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    EDITOR_TEMPLATE_PATH = os.path.join(
        Path(__file__).parent.parent.parent, "data_set/editor_templates/form1.json"
    )
    CLASSES_TEMPLATE_PATH = os.path.join(
        Path(__file__).parent.parent.parent,
        "data_set/editor_templates/form1_classes.json",
    )

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[{"attribute": "TemplateState", "value": 1}],
        )
        team = sa.controller.team
        project = sa.controller.get_project(self.PROJECT_NAME)
        #  todo check
        # time.sleep(10)
        with open(self.EDITOR_TEMPLATE_PATH) as f:
            res = sa.controller.service_provider.projects.attach_editor_template(
                team, project, template=json.load(f)
            )
            assert res.ok
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.CLASSES_TEMPLATE_PATH
        )

    @staticmethod
    def _attach_item(path, name):
        sa.attach_items(path, [{"name": name, "url": "url"}])

    def _base_test(self, path, item):
        with sa.item_context(path, item, overwrite=True) as ic:
            ic.set_component_value("component_id_1", None)
        with sa.item_context(path, item, overwrite=False) as ic:
            assert ic.get_component_value("component_id_1") is None
            ic.set_component_value("component_id_1", "value")
        with self.assertRaisesRegexp(
            FileChangedError, "The file has changed and overwrite is set to False."
        ):
            with sa.item_context(path, item, overwrite=False) as ic:
                assert ic.get_component_value("component_id_1") == "value"
                sa.item_context(path, item, overwrite=True).set_component_value(
                    "component_id_1", "to crash"
                ).save()
                ic.set_component_value("component_id_1", "value")

    def test_overwrite_false(self):
        # test root by folder name
        self._attach_item(self.PROJECT_NAME, "dummy")
        # time.sleep(2)
        self._base_test(self.PROJECT_NAME, "dummy")

        folder = sa.create_folder(self.PROJECT_NAME, folder_name="folder")
        # test from folder by project and folder names
        # time.sleep(2)
        path = f"{self.PROJECT_NAME}/folder"
        self._attach_item(path, "dummy")
        self._base_test(path, "dummy")

        # test from folder by project and folder names as tuple
        path = (self.PROJECT_NAME, "folder")
        self._base_test(path, "dummy")

        # test from folder by project and folder ids as tuple item name as dict
        self._base_test((self._project["id"], folder["id"]), "dummy")

        # test from folder by project and folder ids as tuple and item id
        item = sa.search_items(f"{self.PROJECT_NAME}/folder", "dummy")[0]
        self._base_test((self._project["id"], folder["id"]), item["id"])


class TestEditorContext(BaseTestCase):
    PROJECT_NAME = "TestEditorContext"
    PROJECT_TYPE = "Multimodal"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    COMPONENT_ID = "web_1"
    EDITOR_TEMPLATE_PATH = os.path.join(
        Path(__file__).parent.parent.parent,
        "data_set/sample_llm_editor_context/form.json",
    )

    def setUp(self, *args, **kwargs):

        self._project = sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[{"attribute": "TemplateState", "value": 1}],
        )
        team = sa.controller.team
        project = sa.controller.get_project(self.PROJECT_NAME)
        # time.sleep(10)
        with open(self.EDITOR_TEMPLATE_PATH) as f:
            res = sa.controller.service_provider.projects.attach_editor_template(
                team, project, template=json.load(f)
            )
            assert res.ok
        ...

    def tearDown(self) -> None:
        try:
            sa.delete_project(self.PROJECT_NAME)
        except Exception:
            ...
