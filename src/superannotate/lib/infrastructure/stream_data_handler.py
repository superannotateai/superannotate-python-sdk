import json
import os
from typing import Callable

import aiohttp
from lib.core.reporter import Reporter


class StreamedAnnotations:
    DELIMITER = b"\\n;)\\n"

    def __init__(
        self,
        headers: dict,
        reporter: Reporter,
        callback: Callable = None,
        map_function: Callable = None,
    ):
        self._headers = headers
        self._annotations = []
        self._reporter = reporter
        self._callback: Callable = callback
        self._map_function = map_function

    async def fetch(
        self,
        method: str,
        session: aiohttp.ClientSession,
        url: str,
        data: dict = None,
        params: dict = None,
    ):
        kwargs = {"params": params}
        if data:
            kwargs["json"] = data
        response = await session._request(method, url, **kwargs)
        buffer = b""
        async for line in response.content.iter_any():
            slices = line.split(self.DELIMITER)
            if len(slices) == 1:
                buffer += slices[0]
                continue
            elif slices[0]:
                self._reporter.update_progress()
                yield json.loads(buffer + slices[0])
            for data in slices[1:-1]:
                self._reporter.update_progress()
                yield json.loads(data)
            buffer = slices[-1]
        if buffer:
            yield json.loads(buffer)
            self._reporter.update_progress()

    async def get_data(
        self,
        url: str,
        data: list,
        method: str = "post",
        params=None,
        chunk_size: int = 100,
        verify_ssl: bool = False,
    ):
        async with aiohttp.ClientSession(
            headers=self._headers,
            connector=aiohttp.TCPConnector(ssl=verify_ssl),
        ) as session:
            if chunk_size:
                for i in range(0, len(data), chunk_size):
                    data_to_process = data[i : i + chunk_size]
                    async for annotation in self.fetch(
                        method,
                        session,
                        url,
                        self._process_data(data_to_process),
                        params=params,
                    ):
                        self._annotations.append(
                            self._callback(annotation) if self._callback else annotation
                        )
            else:
                async for annotation in self.fetch(
                    method, session, url, self._process_data(data), params=params
                ):
                    self._annotations.append(
                        self._callback(annotation) if self._callback else annotation
                    )
        return self._annotations

    @staticmethod
    def _store_annotation(path, postfix, annotation: dict, callback: Callable = None):
        os.makedirs(path, exist_ok=True)
        with open(f"{path}/{annotation['metadata']['name']}{postfix}", "w") as file:
            annotation = callback(annotation) if callback else annotation
            json.dump(annotation, file)

    def _process_data(self, data):
        if data and self._map_function:
            return self._map_function(data)
        return data

    async def download_data(
        self,
        url: str,
        data: list,
        download_path: str,
        postfix: str,
        session,
        method: str = "post",
        params=None,
        chunk_size: int = 5000,
    ) -> int:
        """
        Returns the number of items downloaded
        """
        items_downloaded: int = 0
        if chunk_size and data:
            for i in range(0, len(data), chunk_size):
                data_to_process = data[i : i + chunk_size]
                async for annotation in self.fetch(
                    method,
                    session,
                    url,
                    self._process_data(data_to_process),
                    params=params,
                ):
                    self._store_annotation(
                        download_path,
                        postfix,
                        annotation,
                        self._callback,
                    )
                    items_downloaded += 1
        else:
            async for annotation in self.fetch(
                method, session, url, self._process_data(data), params=params
            ):
                self._store_annotation(
                    download_path, postfix, annotation, self._callback
                )
                items_downloaded += 1
        return items_downloaded
