import json
import os
from typing import List
from unittest import TestCase

from pydantic import ValidationError
from pydantic import parse_obj_as

from superannotate.lib.app.serializers import BaseSerializer
from superannotate.lib.core.entities.classes import AnnotationClassEntity
from superannotate.lib.core.entities.classes import AttributeGroup
from superannotate.lib.infrastructure.services.http_client import PydanticEncoder
from superannotate.lib.infrastructure.validators import wrap_error
from tests import DATA_SET_PATH


class TestClassesSerializers(TestCase):
    TEST_LARGE_CLASSES_JSON = "large_classes_json.json"

    @property
    def large_json_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_LARGE_CLASSES_JSON)

    def test_type_user_serializer(self):
        with open(self.large_json_path, "r") as file:
            data_json = json.load(file)
            classes = parse_obj_as(List[AnnotationClassEntity], data_json)
            serializer_data = BaseSerializer.serialize_iterable(classes)
            assert all([isinstance(i.get("type"), str) for i in serializer_data])

    def test_type_api_serializer(self):
        with open(self.large_json_path, "r") as file:
            data_json = json.load(file)
            classes = parse_obj_as(List[AnnotationClassEntity], data_json)
            serializer_data = json.loads(json.dumps(classes, cls=PydanticEncoder))
            assert all([isinstance(i.get("type"), int) for i in serializer_data])

    def test_empty_multiselect_excluded(self):
        annotation_class = AnnotationClassEntity(name="asd", color="blue",
                                                 attribute_groups=[AttributeGroup(name="sad")])
        serializer_data = json.loads(json.dumps(annotation_class, cls=PydanticEncoder))
        assert {'type': 1, 'name': 'asd', 'color': '#0000FF', 'attribute_groups': [{'name': 'sad'}]} == serializer_data

    def test_empty_multiselect_bool_serializer(self):
        annotation_class = AnnotationClassEntity(
            name="asd", color="blue", attribute_groups=[AttributeGroup(name="sad", is_multiselect="True")]
        )
        serializer_data = json.loads(json.dumps(annotation_class, cls=PydanticEncoder))
        assert {'type': 1, 'name': 'asd', 'color': '#0000FF',
                'attribute_groups': [{'name': 'sad', 'is_multiselect': True}]} == serializer_data

    def test_group_type_wrong_arg(self):
        try:
            AnnotationClassEntity(
                name="asd", color="blue",
                attribute_groups=[AttributeGroup(name="sad", is_multiselect=True, group_type="asd")]
            )
        except ValidationError as e:
            assert ['group_type', 'Available', 'values', 'are:', "'radio',", "'checklist',", "'numeric',",
                    "'text'"] == wrap_error(e).split()
