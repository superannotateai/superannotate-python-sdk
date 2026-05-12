import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from src.superannotate import FileChangedError
from src.superannotate import ItemContext
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
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[{"attribute": "TemplateState", "value": 1}],
            form=self.MULTIMODAL_FORM,
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
        with self.assertRaisesRegex(
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


class TestItemContextSetComponentCalledFlag(TestCase):
    def _make_context(self):
        ic = ItemContext(
            controller=MagicMock(),
            project=MagicMock(),
            folder=MagicMock(),
            item=MagicMock(),
            overwrite=True,
        )
        ic._annotation_adapter = MagicMock()
        ic._annotation_adapter.annotation = {"metadata": {}, "data": {}}
        return ic

    def test_dirty_flag_initial_state(self):
        ic = self._make_context()
        self.assertFalse(ic._set_component_called)

    def test_set_component_value_marks_dirty(self):
        ic = self._make_context()
        ic.set_component_value("component_id", "value")
        self.assertTrue(ic._set_component_called)

    def test_save_called_on_exit_after_set_component_value(self):
        ic = self._make_context()
        with patch.object(ItemContext, "save", autospec=True) as save_mock:
            with ic:
                ic.set_component_value("component_id", "value")
            save_mock.assert_called_once_with(ic)

    def test_dirty_flag_reset_after_save(self):
        ic = self._make_context()
        with patch.object(ic, "_set_small_annotation_adapter"), patch.object(
            ic, "_set_large_annotation_adapter"
        ):
            ic.set_component_value("component_id", "value")
            self.assertTrue(ic._set_component_called)
            ic.save()
            self.assertFalse(ic._set_component_called)

    def test_no_double_save_on_exit_after_manual_save(self):
        ic = self._make_context()
        with patch.object(ic, "_set_small_annotation_adapter"), patch.object(
            ic, "_set_large_annotation_adapter"
        ):
            with ic:
                ic.set_component_value("component_id", "value")
                ic.save()
                self.assertEqual(ic._annotation_adapter.save.call_count, 1)
            self.assertEqual(ic._annotation_adapter.save.call_count, 1)

    def test_save_not_called_when_exception_raised(self):
        ic = self._make_context()
        with patch.object(ItemContext, "save", autospec=True) as save_mock:
            with self.assertRaises(RuntimeError):
                with ic:
                    ic.set_component_value("component_id", "value")
                    raise RuntimeError("boom")
            save_mock.assert_not_called()
