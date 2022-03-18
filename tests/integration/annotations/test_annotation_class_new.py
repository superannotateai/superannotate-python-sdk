import os
from pathlib import Path
from unittest import TestCase

import src.superannotate as sa


class TestAnnotationClasses(TestCase):
    PROJECT_NAME = "test_annotation_class_new"
    PROJECT_NAME_JSON = "test_annotation_class_json"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    @classmethod
    def setUpClass(cls):
        cls.tearDownClass()
        project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )
        project_json = sa.create_project(
            cls.PROJECT_NAME_JSON, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )
        cls._project = project
        cls._project_json = project_json

    @classmethod
    def tearDownClass(cls) -> None:
        projects = []
        projects.extend(sa.search_projects(cls.PROJECT_NAME, return_metadata=True))
        projects.extend(sa.search_projects(cls.PROJECT_NAME_JSON, return_metadata=True))
        for project in projects:
            sa.delete_project(project)

    @property
    def classes_json(self):
        return os.path.join(Path(__file__).parent.parent.parent,
            "data_set/sample_project_vector/classes/classes.json",
        )

    def test_create_annotation_class(self):
        sa.create_annotation_class(self.PROJECT_NAME, "tt", "#FFFFFF")
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]['type'], 'object')

    def test_create_annotation_class_from_json(self):
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME_JSON, self.classes_json
        )
        self.assertEqual(len(sa.search_annotation_classes(self.PROJECT_NAME_JSON)), 4)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME_JSON, self.classes_json
        )
        self.assertEqual(len(sa.search_annotation_classes(self.PROJECT_NAME_JSON)), 4)
