import copy
import json
import os
import typing
from typing import Callable

import aiohttp
from lib.core.reporter import Reporter
from superannotate.lib.infrastructure.services.http_client import AIOHttpSession

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

    def get_json(self, data: bytes):
        try:
            return json.loads(data)
        except json.decoder.JSONDecodeError as e:
            self._reporter.log_error(f"Invalud chunk: {str(e)}")

    async def fetch(
        self,
        method: str,
        session: AIOHttpSession,
        url: str,
        data: dict = None,
        params: dict = None,
    ):
        kwargs = {"params": params, "json": {}}
        if "folder_id" in kwargs["params"]:
            kwargs["json"] = {"folder_id": kwargs["params"].pop("folder_id")}
        if data:
            kwargs["json"].update(data)
        response = await session.request(method, url, **kwargs, timeout=TIMEOUT)  # noqa
        buffer = b""
        async for line in response.content.iter_any():
            slices = (buffer + line).split(self.DELIMITER)
            for _slice in slices[:-1]:
                yield self.get_json(_slice)
            buffer = slices[-1]
        if buffer:
            yield self.get_json(buffer)
            self._reporter.update_progress()

    async def list_annotations(
        self,
        method: str,
        url: str,
        data: typing.List[int] = None,
        params: dict = None,
        verify_ssl=False,
    ):
        params = copy.copy(params)
        params["limit"] = len(data)
        annotations = []
        async with AIOHttpSession(
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
                params=copy.copy(params),
            ):
                annotations.append(
                    self._callback(annotation) if self._callback else annotation
                )

        return annotations

    async def download_annotations(
        self,
        method: str,
        url: str,
        download_path,
        data: typing.List[int],
        params: dict = None,
    ):
        params = copy.copy(params)
        params["limit"] = len(data)
        async with AIOHttpSession(
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
                    annotation,
                    self._callback,
                )
                self._items_downloaded += 1

    @staticmethod
    def _store_annotation(path, annotation: dict, callback: Callable = None):
        os.makedirs(path, exist_ok=True)
        with open(f"{path}/{annotation['metadata']['name']}.json", "w") as file:
            annotation = callback(annotation) if callback else annotation
            json.dump(annotation, file)

    def _process_data(self, data):
        if data and self._map_function:
            return self._map_function(data)
        return data
