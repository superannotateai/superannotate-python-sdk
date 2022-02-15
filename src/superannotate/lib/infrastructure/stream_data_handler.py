import json
from typing import Callable
from typing import List

import aiohttp


def map_image_names_to_fetch_streamed_data(data: List[str]):
    mapping = {"image_names": []}
    for image_name in data:
        mapping["image_names"].append(image_name)
    return mapping


class StreamedAnnotations:
    DELIMITER = b";)"

    def __init__(self, headers: dict):
        self._headers = headers
        self._annotations = []

    async def fetch(self, method: str, session: aiohttp.ClientSession, url: str, data: dict = None, params: dict = None):
        response = await session._request(method, url, json=data, params=params)
        buffer = b""
        async for line in response.content:
            slices = line.split(self.DELIMITER)
            if slices[0]:
                self._annotations.append(json.loads(buffer + slices[0]))
            for data in slices[1:-1]:
                self._annotations.append(json.loads(data))
            buffer = slices[-1]
        if buffer:
            self._annotations.append(json.loads(buffer))
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

        async with aiohttp.ClientSession(raise_for_status=True, headers=self._headers,
                                         connector=aiohttp.TCPConnector(ssl=verify_ssl)) as session:

            if chunk_size:
                for i in range(0, len(data), chunk_size):
                    await self.fetch(method, session, url, map_function(data[i:i + chunk_size]), params=params)
            else:
                await self.fetch(method, session, url, map_function(data), params=params)
        return self._annotations
