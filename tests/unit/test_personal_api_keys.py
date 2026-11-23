import json
from unittest import TestCase

import src.superannotate  # noqa: F401  (puts the package dir on sys.path for `lib.*`)
from lib.core.jsx_conditions import EmptyQuery
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import OperatorEnum
from lib.infrastructure.query_builder import PersonalAPIKeyFilterHandler
from lib.infrastructure.query_builder import QueryBuilderChain


class TestBuildParams(TestCase):
    def test_empty(self):
        self.assertEqual(EmptyQuery().build_search_params(), {})

    def test_filters_become_s_param(self):
        query = EmptyQuery() & Filter("status", ["ACTIVE"], OperatorEnum.IN)
        query &= Filter("name", "key", OperatorEnum.CONTAINS)
        params = query.build_search_params()
        self.assertEqual(
            json.loads(params["s"]),
            {
                "$and": [
                    {"status": {"$in": ["ACTIVE"]}},
                    {"name": {"$cont": "key"}},
                ]
            },
        )

    def test_status_filter_handler(self):
        query = QueryBuilderChain([PersonalAPIKeyFilterHandler()]).handle(
            {"status__in": ["Active", "Rotating"]}, EmptyQuery()
        )
        self.assertEqual(
            json.loads(query.build_search_params()["s"]),
            {"$and": [{"status": {"$in": ["ACTIVE", "ROTATING"]}}]},
        )

    def test_any_collection_is_a_json_list(self):
        for collection in (list, tuple, set):
            query = EmptyQuery() & Filter("id", collection([1]), OperatorEnum.IN)

            self.assertEqual(
                json.loads(query.build_search_params()["s"]),
                {"$and": [{"id": {"$in": [1]}}]},
            )
