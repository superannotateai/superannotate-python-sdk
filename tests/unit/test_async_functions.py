import asyncio
from unittest import TestCase

from superannotate import SAClient


sa = SAClient()


class TestAsyncFunctions(TestCase):
    PROJECT_NAME = "TestAsync"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    ATTACH_PAYLOAD = [{"name": f"name_{i}", "url": "url"} for i in range(4)]
    UPLOAD_PAYLOAD = [{"metadata": {"name": f"name_{i}"}} for i in range(4)]

    @classmethod
    def setUpClass(cls):
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )
        sa.attach_items(cls.PROJECT_NAME, cls.ATTACH_PAYLOAD)

    @classmethod
    def tearDownClass(cls):
        sa.delete_project(cls.PROJECT_NAME)

    def test_get_annotations_in_running_event_loop(self):
        async def _test():
            annotations = sa.get_annotations(self.PROJECT_NAME)
            assert len(annotations) == 4

        asyncio.run(_test())

    def test_multiple_get_annotations_in_running_event_loop(self):
        #  TODO add handling of nested loop
        async def nested():
            sa.attach_items(self.PROJECT_NAME, self.ATTACH_PAYLOAD)
            annotations = sa.get_annotations(self.PROJECT_NAME)
            assert len(annotations) == 4

        async def create_task_test():
            import nest_asyncio

            nest_asyncio.apply()
            task1 = asyncio.create_task(nested())
            task2 = asyncio.create_task(nested())
            await task1
            await task2

        asyncio.run(create_task_test())

        async def gather_test():
            import nest_asyncio

            nest_asyncio.apply()
            await asyncio.gather(nested(), nested())

        asyncio.run(gather_test())

    def test_upload_annotations_in_running_event_loop(self):
        async def _test():
            sa.attach_items(self.PROJECT_NAME, self.ATTACH_PAYLOAD)
            annotations = sa.upload_annotations(
                self.PROJECT_NAME, annotations=self.UPLOAD_PAYLOAD
            )
            assert len(annotations["succeeded"]) == 4

        asyncio.run(_test())
