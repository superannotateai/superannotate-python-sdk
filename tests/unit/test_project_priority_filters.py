from unittest import TestCase
from unittest.mock import MagicMock

from lib.core.enums import CustomFieldEntityEnum
from lib.core.exceptions import AppException
from lib.core.jsx_conditions import EmptyQuery
from lib.infrastructure.query_builder import ProjectFilterHandler


class TestProjectPriorityFilters(TestCase):
    def _search(self, **filters):
        handler = ProjectFilterHandler(
            team_id=1,
            project=None,
            service_provider=MagicMock(),
            entity=CustomFieldEntityEnum.PROJECT,
            parent=CustomFieldEntityEnum.TEAM,
        )
        return handler.handle(filters, EmptyQuery()).body_builder()["query"]["search"]

    def test_priority_titles_are_sent_as_backend_values(self):
        self.assertEqual(
            self._search(priority="Highest"), {"$and": [{"priority": {"$eq": 5}}]}
        )
        self.assertEqual(
            self._search(priority__in=["Lowest", "Medium"]),
            {"$and": [{"priority": {"$in": [1, 3]}}]},
        )

    def test_priority_none(self):
        self.assertEqual(
            self._search(priority=None), {"$and": [{"priority": {"$isnull": True}}]}
        )
        self.assertEqual(
            self._search(priority__in=["High", None]),
            {
                "$and": [
                    {
                        "$or": [
                            {"priority": {"$in": [4]}},
                            {"priority": {"$isnull": True}},
                        ]
                    }
                ]
            },
        )

    def test_invalid_priority(self):
        for filters in (
            {"priority": "Urgent"},
            {"priority": "highest"},
            {"priority": 5},
            {"priority__in": ["High", "Urgent"]},
        ):
            with self.assertRaisesRegex(
                AppException,
                "Invalid priority value. Available values: Highest, High, Medium, Low, Lowest.",
            ):
                self._search(**filters)
