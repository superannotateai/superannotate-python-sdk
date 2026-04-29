import os

from src.superannotate import SAClient
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestEntitiesSearchVector(BaseTestCase):
    PROJECT_NAME = "TestEntitiesSearchVector"
    PROJECT_DESCRIPTION = "TestEntitiesSearchVector"
    PROJECT_TYPE = "Vector"
    FOLDER_NAME = "test_folder"
    TEST_FOLDER_PATH = "sample_project_vector"
    TEST_QUERY = "instance(type =bbox )"
    TEST_INVALID_QUERY = "!instance(type =bbox )!"

    @property
    def folder_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_FOLDER_PATH)

    def test_query(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME}",
            self.folder_path,
            annotation_status="InProgress",
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        uploaded, _, _ = sa.upload_annotations_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.folder_path
        )
        assert len(uploaded) == 4

        entities = sa.query(f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.TEST_QUERY)
        self.assertEqual(len(entities), 1)
        assert all(
            [
                entity["path"] == f"{self.PROJECT_NAME}/{self.FOLDER_NAME}"
                for entity in entities
            ]
        )

        try:
            self.assertRaises(
                Exception,
                sa.query(f"{self.PROJECT_NAME}", self.TEST_QUERY, subset="something"),
            )
        except Exception as e:
            self.assertEqual(
                str(e),
                "Subset not found. Use the superannotate.get_subsets() function to get a list of the available subsets.",
            )

    def test_query_on_100(self):
        sa.attach_items(self.PROJECT_NAME, os.path.join(DATA_SET_PATH, "100_urls.csv"))
        entities = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")
        assert len(entities) == 100
        assert (
            sa.controller.query_items_count(
                self.PROJECT_NAME, "metadata(status = NotStarted)"
            )
            == 100
        )

    def test_query_result_list_like_behavior(self):
        """Test that QueryResult behaves like a list for backward compatibility."""
        sa.attach_items(self.PROJECT_NAME, os.path.join(DATA_SET_PATH, "100_urls.csv"))
        result = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")

        # Test len()
        self.assertEqual(len(result), 100)

        # Test indexing
        first_item = result[0]
        self.assertIsInstance(first_item, dict)
        self.assertIn("name", first_item)

        # Test negative indexing
        last_item = result[-1]
        self.assertIsInstance(last_item, dict)

        # Test slicing
        sliced = result[0:5]
        self.assertEqual(len(sliced), 5)

        # Test iteration
        count = 0
        for item in result:
            self.assertIsInstance(item, dict)
            count += 1
        self.assertEqual(count, 100)

        # Test list conversion
        as_list = list(result)
        self.assertEqual(len(as_list), 100)
        self.assertIsInstance(as_list, list)

    def test_query_result_count_method(self):
        """Test that QueryResult.count() returns the count from server."""
        sa.attach_items(self.PROJECT_NAME, os.path.join(DATA_SET_PATH, "100_urls.csv"))
        result = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")

        # Test .count() method
        count = result.count()
        self.assertEqual(count, 100)
        self.assertIsInstance(count, int)

        # Verify count matches len
        self.assertEqual(count, len(result))

    def test_query_result_lazy_loading(self):
        """Test that QueryResult.count() does not trigger data fetching."""
        sa.attach_items(self.PROJECT_NAME, os.path.join(DATA_SET_PATH, "100_urls.csv"))
        result = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")

        # Data should not be loaded yet
        self.assertIsNone(result._data)

        # Calling count() should not load data
        count = result.count()
        self.assertEqual(count, 100)
        self.assertIsNone(result._data)

        # Accessing data should trigger loading
        first_item = result[0]
        self.assertIsNotNone(result._data)
        self.assertIsInstance(first_item, dict)

    def test_query_result_repr(self):
        """Test that QueryResult repr shows the underlying list."""
        sa.attach_items(self.PROJECT_NAME, os.path.join(DATA_SET_PATH, "100_urls.csv"))
        result = sa.query(self.PROJECT_NAME, "metadata(status = NotStarted)")

        # Test __repr__
        repr_str = repr(result)
        self.assertIsInstance(repr_str, str)
        self.assertTrue(repr_str.startswith("["))

    def test_validate_saqul_query(self):
        try:
            self.assertRaises(
                Exception, sa.query(self.PROJECT_NAME, self.TEST_INVALID_QUERY)
            )
        except Exception as e:
            self.assertEqual(str(e), "Incorrect query.")
