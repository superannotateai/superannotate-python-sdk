import copy
import json
import logging
import os
import typing
from typing import Callable

import aiohttp
from lib.core.reporter import Reporter
from lib.infrastructure.services.http_client import AIOHttpSession

_seconds = 2**10
TIMEOUT = aiohttp.ClientTimeout(
    total=_seconds, sock_connect=_seconds, sock_read=_seconds
)

logger = logging.getLogger("sa")


class StreamedAnnotations:
    DELIMITER = "\\n;)\\n"
    DELIMITER_LEN = len(DELIMITER)

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
            return None

    async def fetch(
        self,
        method: str,
        session: AIOHttpSession,
        url: str,
        data: dict = None,
        params: dict = None,
    ):
        kwargs = {"params": params, "json": data}
        if data:
            kwargs["json"].update(data)
        response = await session.request(method, url, **kwargs, timeout=TIMEOUT)  # noqa
        if not response.ok:
            logger.error(response.text)
        buffer = ""
        line_groups = b""
        decoder = json.JSONDecoder()
        async for line in response.content.iter_any():
            line_groups += line
            try:
                buffer += line_groups.decode("utf-8")
                line_groups = b""
            except UnicodeDecodeError:
                continue
            while buffer:
                try:
                    if buffer.startswith(self.DELIMITER):
                        buffer = buffer[self.DELIMITER_LEN :]
                    json_obj, index = decoder.raw_decode(buffer)
                    yield json_obj
                    if len(buffer[index:]) >= self.DELIMITER_LEN:
                        buffer = buffer[index + self.DELIMITER_LEN :]
                    else:
                        buffer = buffer[index:]
                        break
                except json.decoder.JSONDecodeError as e:
                    logger.debug(
                        f"Failed to parse buffer, buffer_len: {len(buffer)} || start buffer:"
                        f" {buffer[:50]} || buffer_end: ...{buffer[-50:]} || error: {e}"
                    )
                    break

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
