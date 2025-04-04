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
        "name": "SDK_test_multi_select",
        "access": {},
        "component_id": CustomFieldType.MULTI_SELECT.value,
        "component_payload": {
            "options": [
                {"value": "option1"},
                {"value": "option2"},
                {"value": "option3"},
            ]
        },
    },
]

FIELD_VALUE_MAP = {
    "SDK_test_text": "test_text_value",
    "SDK_test_date_picker": round(time.time(), 3),
    "SDK_test_numeric": 123,
    "SDK_test_single_select": "option1",
    "SDK_test_multi_select": ["option1", "option2"],
}


SCORE_TEMPLATES = [
    {
        "name": "SDK-my-score-1",
        "description": "",
        "score_type": "rating",
        "payload": {"numberOfStars": 10},
    },
    {
        "name": "SDK-my-score-2",
        "description": "",
        "score_type": "number",
        "payload": {"min": 1, "max": 100, "step": 1},
    },
    {
        "name": "SDK-my-score-3",
        "description": "",
        "score_type": "radio",
        "payload": {"options": [{"value": "1"}, {"value": "2"}, {"value": "3"}]},
    },
]
