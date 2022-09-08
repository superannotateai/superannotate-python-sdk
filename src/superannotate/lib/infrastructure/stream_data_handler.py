import asyncio
import copy
import json
import os
from typing import Callable

import aiohttp
from lib.core.reporter import Reporter

_seconds = 2**10
TIMEOUT = aiohttp.ClientTimeout(
    total=_seconds, sock_connect=_seconds, sock_read=_seconds
)


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
        self._items_downloaded = 0

    async def fetch(
        self,
        method: str,
        session: aiohttp.ClientSession,
        url: str,
        data: dict = None,
        params: dict = None,
    ):
        kwargs = {"params": params, "json": {"folder_id": params.pop("folder_id")}}
        if data:
            kwargs["json"].update(data)
        response = await session._request(method, url, **kwargs, timeout=TIMEOUT)
        buffer = b""
        async for line in response.content.iter_any():
            slices = line.split(self.DELIMITER)
            if len(slices) == 2 and slices[0]:
                self._reporter.update_progress()
                buffer += slices[0]
                yield json.loads(buffer)
                buffer = b""
            elif len(slices) > 2:
                for _slice in slices[:-1]:
                    if not _slice:
                        continue
                    self._reporter.update_progress()
                    yield json.loads(buffer + _slice)
                    buffer = b""
            buffer += slices[-1]
        if buffer:
            yield json.loads(buffer)
            self._reporter.update_progress()

    async def process_chunk(
        self,
        method: str,
        url: str,
        data: dict = None,
        params: dict = None,
        verify_ssl=False,
    ):
        async with aiohttp.ClientSession(
            headers=self._headers,
            timeout=TIMEOUT,
            connector=aiohttp.TCPConnector(ssl=verify_ssl, keepalive_timeout=2**32),
            raise_for_status=True,
        ) as session:
            async for annotation in self.fetch(
                method,
                session,
                url,
                self._process_data(data),
                params=params,
            ):
                self._annotations.append(
                    self._callback(annotation) if self._callback else annotation
                )

    async def store_chunk(
        self,
        method: str,
        url: str,
        download_path,
        postfix,
        data: dict = None,
        params: dict = None,
    ):
        async with aiohttp.ClientSession(
            headers=self._headers,
            timeout=TIMEOUT,
            connector=aiohttp.TCPConnector(ssl=False, keepalive_timeout=2**32),
            raise_for_status=True,
        ) as session:
            async for annotation in self.fetch(
                method,
                session,
                url,
                self._process_data(data),
                params=params,
            ):
                self._annotations.append(
                    self._callback(annotation) if self._callback else annotation
                )
                self._store_annotation(
                    download_path,
                    postfix,
                    annotation,
                    self._callback,
                )
                self._items_downloaded += 1

    async def get_data(
        self,
        url: str,
        data: list,
        method: str = "post",
        params=None,
        chunk_size: int = 5000,
        verify_ssl: bool = False,
    ):
        params["limit"] = chunk_size
        await asyncio.gather(
            *[
                self.process_chunk(
                    method=method,
                    url=url,
                    data=data[i : i + chunk_size],
                    params=copy.copy(params),
                    verify_ssl=verify_ssl,
                )
                for i in range(0, len(data), chunk_size)
            ]
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
        method: str = "post",
        params=None,
        chunk_size: int = 5000,
    ) -> int:
        """
        Returns the number of items downloaded
        """
        params["limit"] = chunk_size
        await asyncio.gather(
            *[
                self.store_chunk(
                    method=method,
                    url=url,
                    data=data[i : i + chunk_size],  # noqa
                    params=copy.copy(params),
                    download_path=download_path,
                    postfix=postfix,
                )
                for i in range(0, len(data), chunk_size)
            ]
        )
        return self._items_downloaded
