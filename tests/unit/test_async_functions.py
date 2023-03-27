import asyncio
import concurrent.futures
from unittest import TestCase

from superannotate import SAClient


sa = SAClient()


class DummyIterator:
    def __init__(self, delay, to):
        self.delay = delay
        self.i = 0
        self.to = to

    def __aiter__(self):
        return self

    async def __anext__(self):
        i = self.i
        if i >= self.to:
            raise StopAsyncIteration
        self.i += 1
        if i:
            await asyncio.sleep(self.delay)
        return i


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

    @staticmethod
    async def nested():
        annotations = sa.get_annotations(TestAsyncFunctions.PROJECT_NAME)
        assert len(annotations) == 4

    def test_get_annotations_in_running_event_loop(self):
        async def _test():
            annotations = sa.get_annotations(self.PROJECT_NAME)
            assert len(annotations) == 4

        asyncio.run(_test())

    def test_create_task_get_annotations_in_running_event_loop(self):
        async def _test():
            task1 = asyncio.create_task(self.nested())
            task2 = asyncio.create_task(self.nested())
            await task1
            await task2

        asyncio.run(_test())

    def test_gather_get_annotations_in_running_event_loop(self):
        async def gather_test():
            await asyncio.gather(self.nested(), self.nested())

        asyncio.run(gather_test())

    def test_gather_async_for(self):
        async def gather_test():
            async for _ in DummyIterator(delay=0.01, to=2):
                annotations = sa.get_annotations(TestAsyncFunctions.PROJECT_NAME)
                assert len(annotations) == 4

        asyncio.run(gather_test())

    def test_upload_annotations_in_running_event_loop(self):
        async def _test():
            annotations = sa.upload_annotations(
                self.PROJECT_NAME, annotations=self.UPLOAD_PAYLOAD
            )
            assert len(annotations["succeeded"]) == 4

        asyncio.run(_test())

    def test_upload_in_threads(self):
        def _test():
            annotations = sa.upload_annotations(
                self.PROJECT_NAME, annotations=self.UPLOAD_PAYLOAD
            )
            assert len(annotations["succeeded"]) == 4
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i in range(8):
                futures.append(executor.submit(_test))
            results = []
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())
            assert all(results)
