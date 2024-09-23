from unittest import TestCase

from src.superannotate import SAClient

sa = SAClient()


class BaseApplicationTestCase(TestCase):
    PROJECT_NAME = ""
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BaseApplicationTestCase.PROJECT_NAME = BaseApplicationTestCase.__class__.__name__

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            projects = sa.search_projects(cls.PROJECT_NAME, return_metadata=True)
            for project in projects:
                try:
                    sa.delete_project(project)
                except Exception as e:
                    print(str(e))
        except Exception as e:
            print(str(e))

    def attach_random_items(self, count=5, name_prefix='example_image_', folder=None):
        path = self.PROJECT_NAME
        if folder:
            path = f"{self.PROJECT_NAME}/{folder}"
        uploaded, _, __ = sa.attach_items(
            path,
            [
                {"name": f"{name_prefix}{i}.jpg", "url": f"url_{i}"}
                for i in range(1, count + 1)
            ],  # noqa
        )
        assert len(uploaded) == count

