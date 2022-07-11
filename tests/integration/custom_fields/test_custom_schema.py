import copy

from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestCustomSchema(BaseTestCase):
    PROJECT_NAME = "test custom field schema"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    PAYLOAD = {
        "test": {
            "type": "number"
        },
        "tester": {
            "type": "number"
        }
    }

    def test_create_schema(self):
        data = sa.create_custom_fields(self.PROJECT_NAME, self.PAYLOAD)
        self.assertEqual(self.PAYLOAD, data)

    def test_(self):
        data = sa.create_custom_fields(self.PROJECT_NAME, {
        "test": {
            "type": "numbaaer"
        },
        "tester": {
            "type": "numbsser"
        }}
                                       )

    def test_create_limit_25(self):
        payload = {i: {"type": "number"} for i in range(26)}
        with self.assertRaisesRegexp(
                Exception, "Maximum number of custom fields is 25. You can only create 25 more custom fields."
        ):
            sa.create_custom_fields(self.PROJECT_NAME, payload)

    def test_create_duplicated(self):
        payload = {
            "1": {"type": "number"}
        }
        with self.assertRaisesRegexp(Exception, "Field name 1 is already used."):
            for i in range(2):
                sa.create_custom_fields(self.PROJECT_NAME, payload)

    def test_get_schema(self):
        sa.create_custom_fields(self.PROJECT_NAME, self.PAYLOAD)
        self.assertEqual(sa.get_custom_fields(self.PROJECT_NAME), self.PAYLOAD)

    def test_delete_schema(self):
        payload = copy.copy(self.PAYLOAD)
        sa.create_custom_fields(self.PROJECT_NAME, payload)
        to_delete_field = list(payload.keys())[0]
        sa.delete_custom_fields(self.PROJECT_NAME, [to_delete_field])
        del payload[to_delete_field]
        self.assertEqual(sa.get_custom_fields(self.PROJECT_NAME), payload)

    def test_upload_delete_custom_values(self):
        sa.create_custom_fields(self.PROJECT_NAME, self.PAYLOAD)
        item_name = "test"
        payload = {"test": 12}
        sa.attach_items(self.PROJECT_NAME, [{"name": item_name, "url": item_name}])
        sa.upload_custom_values(self.PROJECT_NAME, [{item_name: payload}] * 10000)
        data = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")
        assert data[0]["custom_metadata"] == payload
        sa.delete_custom_values(self.PROJECT_NAME, [{item_name: ["test"]}])
        data = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")
        assert data[0]["custom_metadata"] == {}
