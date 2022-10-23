import copy

from src.superannotate import AppException
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
        response = sa.delete_custom_fields(self.PROJECT_NAME, [to_delete_field])
        del payload[to_delete_field]
        assert response == payload
        self.assertEqual(sa.get_custom_fields(self.PROJECT_NAME), payload)

    def test_upload_delete_custom_values_query(self):
        sa.create_custom_fields(self.PROJECT_NAME, self.PAYLOAD)
        item_name = "test"
        payload = {"test": 12}
        sa.attach_items(self.PROJECT_NAME, [{"name": item_name, "url": item_name}])
        response = sa.upload_custom_values(self.PROJECT_NAME, [{item_name: payload}] * 10000)
        assert response == {'failed': [], 'succeeded': [item_name]}
        data = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")
        assert data[0]["custom_metadata"] == payload
        sa.delete_custom_values(self.PROJECT_NAME, [{item_name: ["test"]}])
        data = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")
        assert data[0]["custom_metadata"] == {}

    def test_upload_delete_custom_values_search_items(self):
        sa.create_custom_fields(self.PROJECT_NAME, self.PAYLOAD)
        item_name = "test"
        payload = {"test": 12}
        sa.attach_items(self.PROJECT_NAME, [{"name": item_name, "url": item_name}])
        response = sa.upload_custom_values(self.PROJECT_NAME, [{item_name: payload}] * 10000)
        assert response == {'failed': [], 'succeeded': [item_name]}
        data = sa.search_items(self.PROJECT_NAME, name_contains=item_name, include_custom_metadata=True)
        assert data[0]["custom_metadata"] == payload
        sa.delete_custom_values(self.PROJECT_NAME, [{item_name: ["test"]}])
        data = sa.search_items(self.PROJECT_NAME, name_contains=item_name, include_custom_metadata=True)
        assert data[0]["custom_metadata"] == {}

    def test_search_items(self):
        sa.create_custom_fields(self.PROJECT_NAME, self.PAYLOAD)
        item_name = "test"
        payload = {"test": 12}
        sa.attach_items(self.PROJECT_NAME, [{"name": item_name, "url": item_name}])
        sa.upload_custom_values(self.PROJECT_NAME, [{item_name: payload}] * 10000)
        items = sa.search_items(self.PROJECT_NAME, include_custom_metadata=True)
        assert items[0]["custom_metadata"] == payload

    def test_search_items_without_custom_metadata(self):
        item_name = "test"
        sa.attach_items(self.PROJECT_NAME, [{"name": item_name, "url": item_name}])
        items = sa.search_items(self.PROJECT_NAME)
        assert "custom_metadata" not in items[0]

    def test_get_item_metadata(self):
        sa.create_custom_fields(self.PROJECT_NAME, self.PAYLOAD)
        item_name = "test"
        payload = {"test": 12}
        sa.attach_items(self.PROJECT_NAME, [{"name": item_name, "url": item_name}])
        sa.upload_custom_values(self.PROJECT_NAME, [{item_name: payload}] * 10000)
        item = sa.get_item_metadata(self.PROJECT_NAME, item_name, include_custom_metadata=True)
        assert item["custom_metadata"] == payload

    def test_get_item_metadata_without_custom_metadata(self):
        item_name = "test"
        sa.attach_items(self.PROJECT_NAME, [{"name": item_name, "url": item_name}])
        item = sa.get_item_metadata(self.PROJECT_NAME, item_name)
        assert "custom_metadata" not in item

    def test_create_invalid(self):
        INVALID_SCHEMA = {
            "date": {"type": "sring", "format": "date"},
            "date1": {"type": "string", "format": "dat"},
            "patient_sex": {"type": "string", "enum": [2, "female"]},
            "date_enum": {"type": "string", "format": "date", "enum": ["2022-03-29", "2022-03-29", "2022-05-29"]},
            "date_enum1": {"type": "string", "format": "date", "enum": "2022-03-29"},
            "date_enum2": {"type": "string", "format": "date", "enu": ["2022-03-29"]},
            "medical_specialist": {"type": "string", "format": "email"},
            "medical_specialist1": {"type": "string", "format": "email", "enum": ["email1@gmail.com", "2022-03-29"]},
            "counts": {"type": "numbe"},
            "age_min": {"type": "number", "minimum": "min"},
            "age_range": {"type": "number", "minimum": 30, "maximum": 20, "enum": [20, 23, 120, 12.5, 0.5, -12.3]},
            "age_enum": {"type": "number", "enum": ["string", "string1", "string2"]}
        }
        error_msg = (
            "-Not supported field type for date.\n"
            "-Spec value type of date1 is not valid.\n"
            "-Spec value type of patient_sex is not valid.\n"
            "-Spec values of date_enum should be unique.\n"
            "-Spec value type of date_enum1 is not valid.\n"
            "-Spec value type of medical_specialist1 is not valid.\n"
            "-Not supported field type for counts.\n"
            "-Spec value type of age_min is not valid.\n"
            "-Maximum spec value of age_range can not be less than minimum value.\n"
            "-Minimum spec value of age_range can not be higher than maximum value.\n"
            "-Spec value type of age_enum is not valid."
        )
        with self.assertRaisesRegexp(AppException, error_msg):
            sa.create_custom_fields(self.PROJECT_NAME, INVALID_SCHEMA)
