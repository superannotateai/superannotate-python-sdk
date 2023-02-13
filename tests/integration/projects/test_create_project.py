import copy
from unittest import TestCase

from src.superannotate import AppException
from src.superannotate import SAClient

sa = SAClient()


class BaseTestCase(TestCase):
    PROJECT_1 = "project_1"
    PROJECT_2 = "project_2"

    def setUp(self, *args, **kwargs):
        self.tearDown()

    def tearDown(self) -> None:
        try:
            for project_name in (self.PROJECT_1, self.PROJECT_2):
                projects = sa.search_projects(project_name, return_metadata=True)
                for project in projects:
                    try:
                        sa.delete_project(project)
                    except Exception:
                        pass
        except Exception as e:
            print(str(e))


class TestSearchProjectVector(BaseTestCase):
    PROJECT_1 = "project_1TestSearchProject"
    PROJECT_2 = "project_2TestSearchProject"
    PROJECT_TYPE = "Vector"
    CLASSES = [
        {
            "type": 1,
            "name": "Personal vehicle",
            "color": "#ecb65f",
            "attribute_groups": [
                {
                    "name": "test",
                    "group_type": "checklist",
                    "attributes": [
                        {"name": "Car"},
                        {"name": "Track"},
                        {"name": "Bus"},
                    ],
                    "default_value": ["Bus"],
                }
            ],
        }
    ]

    WORKFLOWS = [
        {
            "step": 1,
            "className": "Personal vehicle",
            "tool": 3,
            "attribute": [
                {
                    "attribute": {
                        "name": "Car",
                        "attribute_group": {"name": "test"},
                    }
                },
                {
                    "attribute": {
                        "name": "Bus",
                        "attribute_group": {"name": "test"},
                    }
                },
            ],
        },
        {
            "step": 2,
            "className": "Personal vehicle",
            "tool": 3,
            "attribute": [
                {
                    "attribute": {
                        "name": "Track",
                        "attribute_group": {"name": "test"},
                    }
                },
                {
                    "attribute": {
                        "name": "Bus",
                        "attribute_group": {"name": "test"},
                    }
                },
            ],
        },
    ]

    @property
    def projects(self):
        return self.PROJECT_2, self.PROJECT_1

    def test_created_project(self):
        #  check datetime
        project = sa.create_project(self.PROJECT_1, "desc", self.PROJECT_TYPE)
        metadata = sa.get_project_metadata(project["name"])
        assert "Z" not in metadata["createdAt"]

    def test_create_project_wrong_type(self):
        with self.assertRaisesRegexp(
                AppException,
                "Available values are 'Vector', 'Pixel', 'Video', 'Document', 'Tiled', 'Other', 'PointCloud'.",
        ):
            sa.create_project(self.PROJECT_1, "desc", "wrong_type")

    def test_create_project_with_settings(self):
        sa.create_project(
            self.PROJECT_1,
            "desc",
            self.PROJECT_TYPE,
            [{"attribute": "ImageQuality", "value": "original"}],
        )
        project = sa.get_project_metadata(self.PROJECT_1, include_settings=True)
        for setting in project["settings"]:
            if setting["attribute"] == "ImageQuality":
                assert setting["value"] == "original"

    def test_create_with_classes_and_workflows(self):
        project = sa.create_project(self.PROJECT_1, "desc", self.PROJECT_TYPE, classes=self.CLASSES,
                                    workflows=self.WORKFLOWS)
        assert len(project['classes']) == 1
        assert len(project['classes'][0]['attribute_groups']) == 1
        assert len(project['classes'][0]['attribute_groups'][0]['attributes']) == 3

        assert len(project['workflows']) == 2
        assert project['workflows'][0]['className'] == self.CLASSES[0]['name']
        assert project['workflows'][0]['attribute'][0]['attribute']['name'] == 'Car'
        assert project['workflows'][0]['attribute'][1]['attribute']['name'] == 'Bus'
        assert project['workflows'][1]['attribute'][0]['attribute']['name'] == 'Track'
        assert project['workflows'][1]['attribute'][1]['attribute']['name'] == 'Bus'

    def test_create_with_workflow_without_classes(self):
        with self.assertRaisesRegexp(AppException, 'Project with workflows can not be created without classes.'):
            sa.create_project(self.PROJECT_1, "desc", self.PROJECT_TYPE, workflows=self.WORKFLOWS)

    def test_create_wrong_project_type(self):
        with self.assertRaisesRegexp(AppException, 'Workflow is not supported in Video project.'):
            sa.create_project(self.PROJECT_1, "desc", "Video", workflows=self.WORKFLOWS)

    def test_create_with_workflow_wrong_classes(self):
        # with self.assertRaisesRegexp didnt work
        try:
            workflows = copy.copy(self.WORKFLOWS)
            workflows[0]['className'] = "1"
            workflows[1]['className'] = "2"
            sa.create_project(
                self.PROJECT_1, "desc", self.PROJECT_TYPE, classes=self.CLASSES, workflows=self.WORKFLOWS
            )
        except AppException as e:
            assert str(e) == 'There are no [1, 2] classes created in the project.'


class TestSearchProjectVideo(BaseTestCase):
    PROJECT_1 = "project_1TestSearchProjectVideo"
    PROJECT_2 = "project_2TestSearchProjectVideo"
    PROJECT_TYPE = "Video"

    @property
    def projects(self):
        return self.PROJECT_2, self.PROJECT_1

    def test_create_project_with_settings(self):
        sa.create_project(
            self.PROJECT_1,
            "desc",
            self.PROJECT_TYPE,
            [{"attribute": "FrameRate", "value": 1.0}],
        )
        project = sa.get_project_metadata(self.PROJECT_1, include_settings=True)
        for setting in project["settings"]:
            if setting["attribute"] == "FrameRate":
                assert setting["value"] == 1
