import json
from typing import Callable

import aiohttp
from lib.core.reporter import Reporter


class StreamedAnnotations:
    DELIMITER = b"\\n;)\\n"

    def __init__(self, headers: dict, reporter: Reporter):
        self._headers = headers
        self._annotations = []
        self._reporter = reporter

    async def fetch(
        self,
        method: str,
        session: aiohttp.ClientSession,
        url: str,
        data: dict = None,
        params: dict = None,
    ):
        response = await session._request(method, url, json=data, params=params)
        buffer = b""
        async for line in response.content.iter_any():
            slices = line.split(self.DELIMITER)
            if len(slices) == 1:
                buffer += slices[0]
                continue
            elif slices[0]:
                self._annotations.append(json.loads(buffer + slices[0]))
                self._reporter.update_progress()
            for data in slices[1:-1]:
                self._annotations.append(json.loads(data))
                self._reporter.update_progress()
            buffer = slices[-1]
        if buffer:
            self._annotations.append(json.loads(buffer))
            self._reporter.update_progress()
        return self._annotations

    async def get_data(
        self,
        url: str,
        data: list,
        method: str = "post",
        params=None,
        chunk_size: int = 100,
        map_function: Callable = lambda x: x,
        verify_ssl: bool = False,
    ):
        async with aiohttp.ClientSession(
            raise_for_status=True,
            headers=self._headers,
            connector=aiohttp.TCPConnector(ssl=verify_ssl),
        ) as session:

            if chunk_size:
                for i in range(0, len(data), chunk_size):
                    data_to_process = data[i : i + chunk_size]
                    await self.fetch(
                        method,
                        session,
                        url,
                        map_function(data_to_process),
                        params=params,
                    )
            else:
                await self.fetch(
                    method, session, url, map_function(data), params=params
                )
        return self._annotations
