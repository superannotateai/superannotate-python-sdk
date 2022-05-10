from unittest import TestCase

from src.superannotate import SAClient


sa = SAClient()


class BaseTestCase(TestCase):
    PROJECT_NAME = ""
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Type"
    TEST_FOLDER_PATH = "data_set"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BaseTestCase.PROJECT_NAME = BaseTestCase.__class__.__name__

    def setUp(self, *args, **kwargs):
        self.tearDown()
        print(self.PROJECT_NAME)
        self._project = sa.create_project(
            self.PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        try:
            projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
            for project in projects:
                try:
                    sa.delete_project(project)
                except Exception:
                    pass
        except Exception as e:
            print(str(e))
