from typing import Any
from typing import Dict

from lib.core.enums import CustomFieldEntityEnum
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase
from tests.integration.work_management.data_set import CUSTOM_FIELD_PAYLOADS
from tests.integration.work_management.data_set import FIELD_VALUE_MAP

sa = SAClient()


class TestProjectCustomFields(BaseTestCase):
    PROJECT_NAME = "TestProjectCustomFields"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "DESCRIPTION"

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        # setup custom fields for test
        cls.tearDownClass()
        for data in CUSTOM_FIELD_PAYLOADS:
            req = sa.controller.service_provider.work_management.create_custom_field_template(
                name=data["name"],
                component_id=data["component_id"],
                entity=CustomFieldEntityEnum.PROJECT,
                parent_entity=CustomFieldEntityEnum.TEAM,
                component_payload=data.get("component_payload", {}),
                access=data["access"],
            )
            assert req.status_code == 201

    @classmethod
    def tearDownClass(cls) -> None:
        # cleanup test custom fields
        bed_custom_fields_name_id_map = {
            i["name"]: i["id"]
            for i in sa.controller.service_provider.work_management.list_custom_field_templates(
                entity=CustomFieldEntityEnum.PROJECT,
                parent_entity=CustomFieldEntityEnum.TEAM,
            ).data[
                "data"
            ]
        }
        for data in CUSTOM_FIELD_PAYLOADS:
            if data["name"] in bed_custom_fields_name_id_map.keys():
                sa.controller.service_provider.work_management.delete_custom_field_template(
                    bed_custom_fields_name_id_map[data["name"]],
                    entity=CustomFieldEntityEnum.PROJECT,
                    parent_entity=CustomFieldEntityEnum.TEAM,
                )

    def _set_custom_field_values(self, field_value_map: Dict[str, Any] = None) -> None:
        if not field_value_map:
            field_value_map = FIELD_VALUE_MAP
        for k, v in field_value_map.items():
            sa.set_project_custom_field(self.PROJECT_NAME, k, v)

    def test_get_project_metadata_without_custom_fields(self):
        project_metadata = sa.get_project_metadata(
            self.PROJECT_NAME, include_custom_fields=False
        )
        assert project_metadata["custom_fields"] == {}

    def test_set_project_custom_field(self):
        # project metadata before set custom field values
        project_metadata = sa.get_project_metadata(
            self.PROJECT_NAME, include_custom_fields=True
        )
        for data in CUSTOM_FIELD_PAYLOADS:
            assert data["name"] in project_metadata["custom_fields"].keys()
            assert not project_metadata["custom_fields"][data["name"]]

        # project metadata after set custom field values
        self._set_custom_field_values()

        project_metadata = sa.get_project_metadata(
            self.PROJECT_NAME, include_custom_fields=True
        )
        for data in CUSTOM_FIELD_PAYLOADS:
            assert data["name"] in project_metadata["custom_fields"].keys()
            assert (
                project_metadata["custom_fields"][data["name"]]
                == FIELD_VALUE_MAP[data["name"]]
            )

    def test_list_projects_by_native_fields(self):
        projects = sa.list_projects(include=["custom_fields"], name=self.PROJECT_NAME)
        assert len(projects) == 1
        assert projects[0]["name"] == self.PROJECT_NAME
        for data in CUSTOM_FIELD_PAYLOADS:
            assert data["name"] in projects[0]["custom_fields"].keys()
            assert not projects[0]["custom_fields"][data["name"]]

        assert not sa.list_projects(
            include=["custom_fields"], name__in=["invalid_name_1", "invalid_name_2"]
        )
        assert (
            len(
                sa.list_projects(
                    include=["custom_fields"], name__contains="TestProjectCustomFie"
                )
            )
            == 1
        )
        assert (
            len(
                sa.list_projects(
                    include=["custom_fields"],
                    name__in=[self.PROJECT_NAME, "other_name"],
                )
            )
            == 1
        )
        assert not sa.list_projects(
            include=["custom_fields"],
            name__in=[self.PROJECT_NAME, "other_name"],
            status="Completed",
        )
        assert (
            len(
                sa.list_projects(
                    include=["custom_fields"],
                    name__in=[self.PROJECT_NAME, "other_name"],
                    status__in=["NotStarted"],
                )
            )
            == 1
        )

    def test_list_projects_by_custom_fields(self):
        # project metadata after set custom field values
        self._set_custom_field_values()
        projects = sa.list_projects(
            include=["custom_fields"], custom_field__SDK_test_numeric=123
        )
        assert len(projects) == 1
        assert projects[0]["name"] == self.PROJECT_NAME
        for data in CUSTOM_FIELD_PAYLOADS:
            assert data["name"] in projects[0]["custom_fields"].keys()
            assert (
                projects[0]["custom_fields"][data["name"]]
                == FIELD_VALUE_MAP[data["name"]]
            )

        assert not sa.list_projects(
            include=["custom_fields"], custom_field__SDK_test_numeric=1
        )
        for p in sa.list_projects(
            include=["custom_fields"], custom_field__SDK_test_numeric__ne=123
        ):
            assert not p["name"] == self.PROJECT_NAME
        assert (
            len(
                sa.list_projects(
                    include=["custom_fields"],
                    custom_field__SDK_test_multy_select__in=["option1", "option2"],
                )
            )
            == 1
        )
        assert (
            len(
                sa.list_projects(
                    include=["custom_fields"],
                    custom_field__SDK_test_single_select="option1",
                )
            )
            == 1
        )
        assert (
            len(
                sa.list_projects(
                    include=["custom_fields"],
                    custom_field__SDK_test_multy_select__contains="option2",
                )
            )
            == 1
        )
        assert not sa.list_projects(
            include=["custom_fields"],
            custom_field__SDK_test_multy_select__contains="invalid_option",
        )
        assert (
            len(
                sa.list_projects(
                    include=["custom_fields"],
                    custom_field__SDK_test_text__contains="test_text_v",
                )
            )
            == 1
        )
