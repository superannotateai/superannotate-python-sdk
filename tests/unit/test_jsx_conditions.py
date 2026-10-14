from unittest import TestCase

from src.superannotate.lib.core.jsx_conditions import Filter
from src.superannotate.lib.core.jsx_conditions import Join
from src.superannotate.lib.core.jsx_conditions import OperatorEnum
from src.superannotate.lib.core.jsx_conditions import OrFilter


class TestCondition(TestCase):
    def test_query_build(self):
        condition = Filter("created", "today", OperatorEnum.GT)
        self.assertEqual(condition.build_query(), "filter=created||$gt||today")

    def test_multiple_query_build(self):
        query = Filter("id", "1,2,3", OperatorEnum.IN) & OrFilter(
            "id", 2, OperatorEnum.EQ
        )
        query &= Join("metadata") & Join("fields", ["field1", "field2"])
        self.assertEqual(
            "filter=id||$in||1%2C2%2C3&or=id||$eq||2&join=metadata&join=fields||field1,field2",
            query.build_query(),
        )

    def test_body_build_none_values(self):
        cases = [
            (
                Filter("priority", None, OperatorEnum.EQ),
                [{"priority": {"$isnull": True}}],
            ),
            (
                Filter("priority", None, OperatorEnum.NE),
                [{"priority": {"$notnull": True}}],
            ),
            (
                Filter("priority", [None, 4], OperatorEnum.IN),
                [
                    {
                        "$or": [
                            {"priority": {"$in": [4]}},
                            {"priority": {"$isnull": True}},
                        ]
                    }
                ],
            ),
            (
                Filter("priority", [None], OperatorEnum.IN),
                [{"priority": {"$isnull": True}}],
            ),
            (
                Filter("priority", [None, 4], OperatorEnum.NOTIN),
                [{"priority": {"$notnull": True}}, {"priority": {"$notin": [4]}}],
            ),
            (
                Filter("priority", [None], OperatorEnum.NOTIN),
                [{"priority": {"$notnull": True}}],
            ),
            (
                Filter("priority", [4, 5], OperatorEnum.IN),
                [{"priority": {"$in": [4, 5]}}],
            ),
        ]
        for condition, expected in cases:
            self.assertEqual(condition.body_build(), ("$and", expected))
