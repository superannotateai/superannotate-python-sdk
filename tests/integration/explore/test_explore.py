import time
from unittest import TestCase

from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()

ITEM_KEYS = {
    "id",
    "name",
    "folder_id",
    "comments",
    "annotation_status",
    "path",
    "approval_status",
    "createdAt",
    "updatedAt",
    "meta",
    "instances",
    "custom_metadata",
    "subset_ids",
    "category_id",
    "category_name",
    "assignment",
    "last_action",
    "score",
    "is_pinned",
    "folder_name",
    "is_root_folder",
}


class TestExploreMM(TestCase):
    PROJECT_NAME = "TestExploreMM"
    PROJECT_DESCRIPTION = "TestExploreMM"
    PROJECT_TYPE = "Multimodal"
    FOLDER_NAME = "test_folder"
    SUBSET_NAME = "test_subset"
    QUERY = '_status = "NotStarted"'
    MULTIMODAL_FORM = {
        "components": [
            {
                "id": "r_qx07c6",
                "type": "audio",
                "permissions": [],
                "hasTooltip": False,
                "exclude": False,
                "label": "",
                "value": "",
            }
        ],
        "readme": "",
    }

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[{"attribute": "TemplateState", "value": 1}],
            form=self.MULTIMODAL_FORM,
        )

    def tearDown(self) -> None:
        try:
            projects = sa.list_projects(name=self.PROJECT_NAME)
            for project in projects:
                try:
                    sa.delete_project(project=project["id"])
                except Exception as e:
                    print(str(e))
        except Exception as e:
            print(str(e))

    @property
    def folder_path(self):
        return f"{self.PROJECT_NAME}/{self.FOLDER_NAME}"

    def test_query(self):
        # more than one page (25 items), so paging is exercised
        sa.generate_items(self.PROJECT_NAME, 60, name="a")

        items = sa.explore.query(self.PROJECT_NAME, self.QUERY)

        assert len(items) == 60
        assert {i["name"] for i in items} == {f"a_{i:05d}" for i in range(1, 61)}
        assert all(set(i) == ITEM_KEYS for i in items)
        assert all(i["is_root_folder"] for i in items)

    def test_annotation_status_is_a_name(self):
        sa.generate_items(self.PROJECT_NAME, 3, name="a")
        sa.set_annotation_statuses(self.PROJECT_NAME, "InProgress", ["a_00001"])

        # the explore index picks up a status change asynchronously
        for _ in range(15):
            in_progress = sa.explore.query(self.PROJECT_NAME, '_status = "InProgress"')
            if len(in_progress):
                break
            time.sleep(2)
        not_started = sa.explore.query(self.PROJECT_NAME, self.QUERY)

        assert [i["annotation_status"] for i in in_progress] == ["InProgress"]
        assert {i["annotation_status"] for i in not_started} == {"NotStarted"}
        # same representation as list_items
        listed = {
            i["name"]: i["annotation_status"] for i in sa.list_items(self.PROJECT_NAME)
        }
        queried = {
            i["name"]: i["annotation_status"] for i in [*in_progress, *not_started]
        }
        assert queried == listed

    def test_query_count(self):
        sa.generate_items(self.PROJECT_NAME, 30, name="a")

        assert sa.explore.query(self.PROJECT_NAME, self.QUERY).count() == 30

    def test_query_in_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.generate_items(self.PROJECT_NAME, 3, name="root")
        sa.generate_items(self.folder_path, 5, name="folder")

        items = sa.explore.query(self.folder_path, self.QUERY)

        assert len(items) == 5
        assert {i["folder_name"] for i in items} == {self.FOLDER_NAME}
        assert sa.explore.query(self.folder_path, self.QUERY).count() == 5
        assert sa.explore.query(self.PROJECT_NAME, self.QUERY).count() == 8

    def test_query_by_ids(self):
        folder = sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.generate_items(self.folder_path, 5, name="folder")

        by_project_id = sa.explore.query(self._project["id"], self.QUERY)
        by_ids = sa.explore.query((self._project["id"], folder["id"]), self.QUERY)

        assert len(by_project_id) == 5
        assert len(by_ids) == 5

    def test_subsets(self):
        sa.generate_items(self.PROJECT_NAME, 10, name="a")
        items = sa.explore.query(self.PROJECT_NAME, self.QUERY)

        result = sa.explore.add_items_to_subset(
            self.PROJECT_NAME, self.SUBSET_NAME, items[:4]
        )

        assert len(result["succeeded"]) == 4
        assert self.SUBSET_NAME in [
            s["name"] for s in sa.explore.get_subsets(self.PROJECT_NAME)
        ]
        in_subset = sa.explore.query(self.PROJECT_NAME, subset=self.SUBSET_NAME)
        assert {i["id"] for i in in_subset} == {i["id"] for i in items[:4]}
        assert (
            sa.explore.query(
                self.PROJECT_NAME, self.QUERY, subset=self.SUBSET_NAME
            ).count()
            == 4
        )

    def test_add_items_to_subset_by_name_and_path(self):
        sa.generate_items(self.PROJECT_NAME, 2, name="a")

        result = sa.explore.add_items_to_subset(
            self._project["id"],
            self.SUBSET_NAME,
            [{"name": "a_00001", "path": self.PROJECT_NAME}],
        )

        assert len(result["succeeded"]) == 1

    def test_query_or_subset_required(self):
        with self.assertRaisesRegex(AppException, r"^Provide 'query' or 'subset'$"):
            sa.explore.query(self.PROJECT_NAME)

    def test_subset_not_found(self):
        # QueryResult is lazy - the subset is resolved when the data or count is read
        result = sa.explore.query(self.PROJECT_NAME, self.QUERY, subset="missing")
        with self.assertRaisesRegex(AppException, r"^Subset not found$"):
            result.data()
        with self.assertRaisesRegex(AppException, r"^Subset not found$"):
            result.count()

    def test_invalid_query(self):
        sa.generate_items(self.PROJECT_NAME, 1, name="a")
        result = sa.explore.query(self.PROJECT_NAME, "!invalid query!")

        with self.assertRaisesRegex(AppException, r"^Expected a field but found '!'$"):
            result.data()
        with self.assertRaisesRegex(AppException, r"^Expected a field but found '!'$"):
            result.count()

    def test_unknown_field_in_query(self):
        sa.generate_items(self.PROJECT_NAME, 1, name="a")

        with self.assertRaisesRegex(
            AppException, r"^Unknown built-in field _nosuchfield$"
        ):
            sa.explore.query(self.PROJECT_NAME, '_nosuchfield = "x"').data()

    def test_project_not_found(self):
        with self.assertRaisesRegex(AppException, r"^Project not found\.$"):
            sa.explore.query("TestExploreMM-missing", self.QUERY)
        with self.assertRaisesRegex(AppException, r"^Project not found\.$"):
            sa.explore.query(999999999, self.QUERY)

    def test_folder_not_found(self):
        with self.assertRaisesRegex(AppException, r"^Folder not found\.$"):
            sa.explore.query(f"{self.PROJECT_NAME}/missing", self.QUERY)

    def test_folder_id_not_found(self):
        with self.assertRaisesRegex(
            AppException, r"^You do not have sufficient access to get this items\.$"
        ):
            sa.explore.query((self._project["id"], 999999999), self.QUERY)

    def test_query_invalid_arguments(self):
        with self.assertRaisesRegex(
            AppException,
            r"argument at index 2\s+String should have at least 1 character",
        ):
            sa.explore.query(self.PROJECT_NAME, "")
        with self.assertRaisesRegex(
            AppException, r"argument at index 2\s+Input should be a valid string"
        ):
            sa.explore.query(self.PROJECT_NAME, 123)
        with self.assertRaisesRegex(
            AppException, r"argument at index 1\s+Input should be a valid string"
        ):
            sa.explore.query(1.5, self.QUERY)

    def test_get_subsets_errors(self):
        with self.assertRaisesRegex(AppException, r"^Project not found\.$"):
            sa.explore.get_subsets("TestExploreMM-missing")
        with self.assertRaisesRegex(
            AppException, r"argument at index 1\s+Input should be a valid string"
        ):
            sa.explore.get_subsets(None)

    def test_add_items_to_subset_errors(self):
        with self.assertRaisesRegex(AppException, r"^Project not found\.$"):
            sa.explore.add_items_to_subset(
                "TestExploreMM-missing", self.SUBSET_NAME, [{"id": 1}]
            )
        with self.assertRaisesRegex(
            AppException,
            r"argument at index 2\s+String should have at least 1 character",
        ):
            sa.explore.add_items_to_subset(self.PROJECT_NAME, "", [{"id": 1}])
        with self.assertRaisesRegex(
            AppException, r"argument at index 3\s+Input should be a valid list"
        ):
            sa.explore.add_items_to_subset(
                self.PROJECT_NAME, self.SUBSET_NAME, "not a list"
            )

    def test_add_items_to_subset_skips_unresolvable_items(self):
        sa.generate_items(self.PROJECT_NAME, 1, name="a")
        missing_path = {"name": "a_00001"}
        unknown_item = {"name": "missing", "path": self.PROJECT_NAME}

        result = sa.explore.add_items_to_subset(
            self.PROJECT_NAME, self.SUBSET_NAME, [missing_path, unknown_item]
        )

        assert result == {
            "succeeded": [],
            "failed": [],
            "skipped": [missing_path, unknown_item],
        }


class TestExploreVector(BaseTestCase):
    PROJECT_NAME = "TestExploreVector"
    PROJECT_TYPE = "Vector"

    def test_unsupported_project_type(self):
        self._attach_items(count=1)
        result = sa.explore.query(self.PROJECT_NAME, '_status = "NotStarted"')

        with self.assertRaisesRegex(AppException, r"^Unsupported project type\.$"):
            result.data()
        with self.assertRaisesRegex(AppException, r"^Unsupported project type\.$"):
            result.count()


class TestExploreDeprecations(TestCase):
    PROJECT_NAME = "TestExploreDeprecations"
    PROJECT_TYPE = "Vector"

    @classmethod
    def setUpClass(cls):
        cls.tearDownClass()
        sa.create_project(cls.PROJECT_NAME, "desc", cls.PROJECT_TYPE)
        sa.attach_items(cls.PROJECT_NAME, [{"name": "a.jpg", "url": "url_1"}])

    @classmethod
    def tearDownClass(cls):
        for project in sa.list_projects(name=cls.PROJECT_NAME):
            sa.delete_project(project["id"])

    def test_query(self):
        with self.assertWarnsRegex(
            DeprecationWarning, r"query\(\) will be deprecated.*4\.7\.0"
        ):
            result = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")
        with self.assertWarnsRegex(
            DeprecationWarning, r"query\(\)\.count\(\) will be deprecated.*4\.7\.0"
        ):
            assert result.count() == 1

    def test_get_subsets(self):
        with self.assertWarnsRegex(
            DeprecationWarning, r"get_subsets\(\) will be deprecated.*4\.7\.0"
        ):
            sa.get_subsets(self.PROJECT_NAME)

    def test_add_items_to_subset(self):
        with self.assertWarnsRegex(
            DeprecationWarning, r"add_items_to_subset\(\) will be deprecated.*4\.7\.0"
        ):
            sa.add_items_to_subset(
                self.PROJECT_NAME,
                "subset",
                [{"name": "a.jpg", "path": self.PROJECT_NAME}],
            )
