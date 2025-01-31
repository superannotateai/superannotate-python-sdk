from unittest import TestCase

from src.superannotate import SAClient
from src.superannotate.lib.core.enums import CustomFieldEntityEnum
from tests.integration.work_management.data_set import CUSTOM_FIELD_PAYLOADS

sa = SAClient()


class TestWorkManagement(TestCase):
    USER_TEMPLATE_NAME = "user_field"

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        # setup custom fields for test
        cls.tearDownClass()
        for data in CUSTOM_FIELD_PAYLOADS:
            req = sa.controller.service_provider.work_management.create_custom_field_template(
                name=data["name"],
                component_id=data["component_id"],
                entity=CustomFieldEntityEnum.CONTRIBUTOR,
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
                entity=CustomFieldEntityEnum.CONTRIBUTOR,
                parent_entity=CustomFieldEntityEnum.TEAM,
            ).data[
                "data"
            ]
        }
        for data in CUSTOM_FIELD_PAYLOADS:
            if data["name"] in bed_custom_fields_name_id_map.keys():
                sa.controller.service_provider.work_management.delete_custom_field_template(
                    bed_custom_fields_name_id_map[data["name"]],
                    entity=CustomFieldEntityEnum.CONTRIBUTOR,
                    parent_entity=CustomFieldEntityEnum.TEAM,
                )

    def test_get_set_user_metadata(self):
        users = sa.list_users()
        scapegoat = [u for u in users if u["role"] == "Contributor"][0]
        assert not scapegoat["custom_fields"]
        custom_field_to_set = CUSTOM_FIELD_PAYLOADS[0]
        sa.set_user_custom_field(
            scapegoat["email"],
            custom_field_name=custom_field_to_set["name"],
            value="Dummy data",
        )
        scapegoat = sa.list_users(include=["custom_fields"], email=scapegoat["email"])[
            0
        ]
        assert scapegoat["custom_fields"][custom_field_to_set["name"]] == "Dummy data"
        scapegoat = sa.get_user_metadata(scapegoat["email"], include=["custom_fields"])
        assert scapegoat["custom_fields"][custom_field_to_set["name"]] == "Dummy data"
        kwargs = {
            "include": ["custom_fields"],
            f"custom_field__{custom_field_to_set['name']}__contains": "mmy",
        }
        users = sa.list_users(**kwargs)
        assert len(users) == 1
        assert users[0]["custom_fields"][custom_field_to_set["name"]] == "Dummy data"
