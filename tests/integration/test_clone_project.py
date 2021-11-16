from unittest import TestCase

import src.superannotate as sa


class TestCloneProject(TestCase):
    PROJECT_NAME_1 = "test_create_like_project_1"
    PROJECT_NAME_2 = "test_create_like_project_2"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        sa.delete_project(self.PROJECT_NAME_1)
        sa.delete_project(self.PROJECT_NAME_2)
