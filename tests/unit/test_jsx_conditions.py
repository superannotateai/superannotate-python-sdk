from unittest import TestCase

from src.superannotate.lib.core.jsx_conditions import Filter
from src.superannotate.lib.core.jsx_conditions import Join
from src.superannotate.lib.core.jsx_conditions import OperatorEnum
from src.superannotate.lib.core.jsx_conditions import OrFilter


class TestCondition(TestCase):
    def test_query_build(self):
        condition = Filter("created", "today", OperatorEnum.GT)
        self.assertEquals(condition.build_query(), "filter=created||$gt||today")

    def test_multiple_query_build(self):
        query = Filter("id", "1,2,3", OperatorEnum.IN) & OrFilter(
            "id", 2, OperatorEnum.EQ
        )
        query &= Join("metadata") & Join("fields", ["field1", "field2"])
        self.assertEquals(
            "filter=id||$in||1,2,3&or=id||$eq||2&join=metadata&join=fields||field1,field2",
            query.build_query(),
        )
