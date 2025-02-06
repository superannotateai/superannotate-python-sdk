import time
from unittest import TestCase

from lib.core.exceptions import AppException
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
        # text field
        sa.set_user_custom_field(
            scapegoat["email"],
            custom_field_name="SDK_test_text",
            value="Dummy data",
        )
        scapegoat = sa.list_users(include=["custom_fields"], email=scapegoat["email"])[
            0
        ]
        assert scapegoat["custom_fields"]["SDK_test_text"] == "Dummy data"
        scapegoat = sa.get_user_metadata(scapegoat["email"], include=["custom_fields"])
        assert scapegoat["custom_fields"]["SDK_test_text"] == "Dummy data"
        kwargs = {
            "include": ["custom_fields"],
            "custom_field__SDK_test_text__contains": "mmy",
        }
        users = sa.list_users(**kwargs)
        assert len(users) == 1
        assert users[0]["custom_fields"]["SDK_test_text"] == "Dummy data"

        # multi select field
        sa.set_user_custom_field(
            scapegoat["email"],
            custom_field_name="SDK_test_multi_select",
            value=["option1", "option2"],
        )
        assert (
            len(
                sa.list_users(
                    include=["custom_fields"],
                    custom_field__SDK_test_multi_select=["option1", "option2"],
                )
            )
            == 1
        )

        # single select field
        sa.set_user_custom_field(
            scapegoat["email"],
            custom_field_name="SDK_test_single_select",
            value="option1",
        )
        assert (
            len(
                sa.list_users(
                    include=["custom_fields"],
                    custom_field__SDK_test_single_select__contains="option1",
                )
            )
            == 1
        )

        # numeric field
        sa.set_user_custom_field(
            scapegoat["email"],
            custom_field_name="SDK_test_numeric",
            value=5,
        )
        assert (
            len(
                sa.list_users(
                    include=["custom_fields"], custom_field__SDK_test_numeric__lt=10
                )
            )
            == 1
        )

    def test_list_users(self):
        users = sa.list_users()
        all_contributors = [u for u in users if u["role"] == "Contributor"]
        all_confirmed = [u for u in users if u["state"] == "Confirmed"]
        all_pending = [u for u in users if u["state"] == "Pending"]
        scapegoat = all_contributors[0]
        assert not scapegoat["custom_fields"]

        # by date_picker
        value = round(time.time(), 3)
        sa.set_user_custom_field(
            scapegoat["email"],
            custom_field_name="SDK_test_date_picker",
            value=value,
        )
        scapegoat = sa.list_users(
            include=["custom_fields"],
            email=scapegoat["email"],
            custom_field__SDK_test_date_picker=value,
        )[0]
        assert scapegoat["custom_fields"]["SDK_test_date_picker"] == value

        # by email__contains
        assert len(sa.list_users(email__contains="@superannotate.com")) == len(users)

        # by role
        assert len(sa.list_users(role="contributor")) == len(all_contributors)
        assert len(sa.list_users(role__in=["contributor"])) == len(all_contributors)
        with self.assertRaisesRegexp(AppException, "Invalid user role provided."):
            sa.list_users(role__in=["invalid_role"])

        # by state
        assert len(sa.list_users(state="CONFIRMED")) == len(all_confirmed)
        assert len(sa.list_users(state__in=["PENDING"])) == len(all_pending)
        with self.assertRaisesRegexp(AppException, "Invalid user state provided."):
            assert len(sa.list_users(state__in=["invalid_state"])) == len(all_pending)

    def test_get_user_metadata_invalid(self):
        with self.assertRaisesRegexp(AppException, "User not found."):
            sa.get_user_metadata("invalid_user")

    def test_set_user_custom_field_validation(self):
        error_template = (
            "Invalid input: The provided value is not valid.\nExpected type: {type}."
        )
        error_template_select = error_template + "\nValid options are: {options}."
        users = sa.list_users()
        scapegoat = [u for u in users if u["role"] == "Contributor"][0]
        # test for text
        with self.assertRaisesRegexp(AppException, error_template.format(type="str")):
            sa.set_user_custom_field(scapegoat["email"], "SDK_test_text", 123)

        # test for numeric
        with self.assertRaisesRegexp(
            AppException, error_template.format(type="numeric")
        ):
            sa.set_user_custom_field(
                scapegoat["email"], "SDK_test_numeric", "invalid value"
            )

        # test for date_picker
        with self.assertRaisesRegexp(
            AppException, error_template.format(type="numeric")
        ):
            sa.set_user_custom_field(
                scapegoat["email"], "SDK_test_date_picker", "invalid value"
            )

        # test for multi_select
        with self.assertRaisesRegexp(
            AppException,
            error_template_select.format(type="list", options="option1, option2"),
        ):
            sa.set_user_custom_field(
                scapegoat["email"], "SDK_test_multi_select", "invalid value"
            )

        # test for select
        with self.assertRaisesRegexp(
            AppException,
            error_template_select.format(type="str", options="option1, option2"),
        ):
            sa.set_user_custom_field(scapegoat["email"], "SDK_test_single_select", 123)
