from unittest import TestCase

from src.superannotate import AppException
from superannotate import SAClient

sa = SAClient()


class TestSetProjectPriority(TestCase):
    PROJECT_NAME = "test_set_project_priority"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    PROJECT_PRIORITIES = ["Highest", "High", "Medium", "Low", "Lowest"]
    INVALID_PRIORITY_ERROR = (
        "Invalid priority value. Available values: Highest, High, Medium, Low, Lowest."
    )

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )

    @classmethod
    def tearDownClass(cls) -> None:
        for project in sa.list_projects(name=cls.PROJECT_NAME):
            sa.delete_project(project["id"])

    def test_set_project_priority(self):
        with self.assertLogs("sa", level="INFO") as cm:
            for index, priority in enumerate(self.PROJECT_PRIORITIES):
                sa.set_project_priority(project=self.PROJECT_NAME, priority=priority)
                project = sa.get_project_metadata(self.PROJECT_NAME)
                self.assertEqual(
                    f"INFO:sa:Successfully changed the priority of project "
                    f"{self.PROJECT_NAME} to {priority}.",
                    cm.output[index],
                )
                self.assertEqual(priority, project["priority"])
            self.assertEqual(len(cm.output), len(self.PROJECT_PRIORITIES))

    def test_set_project_priority_by_id(self):
        project_id = sa.get_project_metadata(self.PROJECT_NAME)["id"]
        sa.set_project_priority(project=project_id, priority="Low")
        project = sa.get_project_metadata(project_id)
        self.assertEqual(project["priority"], "Low")

    def test_set_project_priority_via_invalid_priority(self):
        for priority in ("Urgent", "highest", ""):
            with self.assertRaisesRegex(AppException, self.INVALID_PRIORITY_ERROR):
                sa.set_project_priority(project=self.PROJECT_NAME, priority=priority)

    def test_clear_project_priority(self):
        sa.set_project_priority(project=self.PROJECT_NAME, priority="High")
        with self.assertLogs("sa", level="INFO") as cm:
            sa.set_project_priority(project=self.PROJECT_NAME, priority=None)
        self.assertEqual(
            f"INFO:sa:Successfully changed the priority of project "
            f"{self.PROJECT_NAME} to None.",
            cm.output[0],
        )
        project = sa.get_project_metadata(self.PROJECT_NAME)
        self.assertIsNone(project["priority"])

    def test_set_project_priority_via_invalid_project(self):
        with self.assertRaisesRegex(AppException, "Project not found."):
            sa.set_project_priority(project="Invalid name", priority="High")

    def test_list_projects_by_priority(self):
        sa.set_project_priority(project=self.PROJECT_NAME, priority="High")
        name = self.PROJECT_NAME

        projects = sa.list_projects(name=name, priority="High")
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["priority"], "High")

        self.assertFalse(sa.list_projects(name=name, priority="Low"))
        self.assertEqual(
            len(sa.list_projects(name=name, priority__in=["Highest", "High"])), 1
        )
        self.assertFalse(sa.list_projects(name=name, priority__notin=["High"]))
        self.assertEqual(len(sa.list_projects(name=name, priority__ne="Low")), 1)
        self.assertFalse(sa.list_projects(name=name, priority__ne="High"))
        self.assertEqual(len(sa.list_projects(name=name, priority__notin=["Low"])), 1)
        self.assertFalse(sa.list_projects(name=name, priority=None))
        self.assertEqual(len(sa.list_projects(name=name, priority__ne=None)), 1)
        self.assertFalse(sa.list_projects(name=name, priority__in=[None, "Low"]))
        self.assertEqual(
            len(sa.list_projects(name=name, priority__in=[None, "High"])), 1
        )
        self.assertEqual(len(sa.list_projects(name=name, priority__notin=[None])), 1)

        sa.set_project_priority(project=self.PROJECT_NAME, priority=None)
        projects = sa.list_projects(name=name, priority=None)
        self.assertEqual(len(projects), 1)
        self.assertIsNone(projects[0]["priority"])
        self.assertFalse(sa.list_projects(name=name, priority="High"))
        self.assertFalse(sa.list_projects(name=name, priority__ne=None))
        self.assertEqual(len(sa.list_projects(name=name, priority__in=[None])), 1)
        self.assertEqual(
            len(sa.list_projects(name=name, priority__in=[None, "High"])), 1
        )
        self.assertFalse(sa.list_projects(name=name, priority__notin=[None, "Low"]))
        self.assertEqual(len(sa.list_projects(name=name, priority__notin=["Low"])), 1)

    def test_list_projects_by_invalid_priority(self):
        with self.assertRaisesRegex(AppException, self.INVALID_PRIORITY_ERROR):
            sa.list_projects(priority="Urgent")
        with self.assertRaisesRegex(AppException, self.INVALID_PRIORITY_ERROR):
            sa.list_projects(priority__in=["High", "Urgent"])
