import time

from src.superannotate.lib.core.enums import CustomFieldType


CUSTOM_FIELD_PAYLOADS = [
    {
        "name": "SDK_test_text",
        "access": {},
        "component_id": CustomFieldType.Text.value,
    },
    {
        "name": "SDK_test_date_picker",
        "access": {},
        "component_id": CustomFieldType.DATE_PICKER.value,
    },
    {
        "name": "SDK_test_numeric",
        "access": {},
        "component_payload": {
            "configs": {"min": None, "max": None, "step": None, "suffix": None}
        },
        "component_id": CustomFieldType.NUMERIC.value,
    },
    {
        "name": "SDK_test_single_select",
        "access": {},
        "component_id": CustomFieldType.SINGLE_SELECT.value,
        "component_payload": {"options": [{"value": "option1"}, {"value": "option2"}]},
    },
    {
        "name": "SDK_test_multy_select",
        "access": {},
        "component_id": CustomFieldType.MULTI_SELECT.value,
        "component_payload": {"options": [{"value": "option1"}, {"value": "option2"}]},
    },
]

FIELD_VALUE_MAP = {
    "SDK_test_text": "test_text_value",
    "SDK_test_date_picker": float(int(time.time())),
    "SDK_test_numeric": 123,
    "SDK_test_single_select": "option1",
    "SDK_test_multy_select": ["option1", "option2"],
}
