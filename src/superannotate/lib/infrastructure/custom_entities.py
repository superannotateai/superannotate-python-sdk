from lib.core.enums import CustomFieldType
from lib.core.jsx_conditions import OperatorEnum
from typing_extensions import Any


FIELD_TYPE_SUPPORTED_OPERATIONS_MAPPING = {
    CustomFieldType.Text: [
        OperatorEnum.EQ,
        OperatorEnum.IN,
        OperatorEnum.NOTIN,
        OperatorEnum.CONTAINS,
    ],
    CustomFieldType.MULTI_SELECT: [OperatorEnum.EQ, OperatorEnum.NOTIN],
    CustomFieldType.SINGLE_SELECT: [
        OperatorEnum.EQ,
        OperatorEnum.IN,
        OperatorEnum.NOTIN,
        OperatorEnum.CONTAINS,
    ],
    CustomFieldType.DATE_PICKER: [OperatorEnum.GT, OperatorEnum.LT, OperatorEnum.EQ],
    CustomFieldType.NUMERIC: [
        OperatorEnum.GT,
        OperatorEnum.LT,
        OperatorEnum.EQ,
        OperatorEnum.IN,
        OperatorEnum.NOTIN,
    ],
}

# todo implement
FIELD_TYPE_BED_OPERATIONS_MAPPING = {
    CustomFieldType.MULTI_SELECT: {OperatorEnum.EQ: OperatorEnum.IN},
    CustomFieldType.DATE_PICKER: {OperatorEnum.EQ: OperatorEnum.IS},
}


def generate_schema(base_schema: dict, custom_field_templates) -> dict:
    annotations = base_schema
    for custom_field_template in custom_field_templates:
        for operator in FIELD_TYPE_SUPPORTED_OPERATIONS_MAPPING[
            CustomFieldType(custom_field_template["component_id"])
        ]:
            condition = f"custom_field__{custom_field_template['name']}"
            if operator != OperatorEnum.EQ:
                condition = condition + f"__{operator.name.lower()}"
            annotations[condition] = Any
    return annotations
