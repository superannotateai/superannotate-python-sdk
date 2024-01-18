import asyncio
import io
import json
import logging
import platform
import threading
import time
import urllib.parse
from contextlib import contextmanager
from functools import lru_cache
from typing import Any
from typing import Dict
from typing import List

import aiohttp
import requests
from lib.core.exceptions import AppException
from lib.core.service_types import ServiceResponse
from lib.core.serviceproviders import BaseClient
from requests.adapters import HTTPAdapter
from requests.adapters import Retry
from superannotate import __version__

try:
    from pydantic.v1 import BaseModel
    from pydantic.v1 import parse_obj_as
except ImportError:
    from pydantic import BaseModel
    from pydantic import parse_obj_as

logger = logging.getLogger("sa")


class PydanticEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return json.loads(obj.json(exclude_none=True))
        return json.JSONEncoder.default(self, obj)


class HttpClient(BaseClient):
    AUTH_TYPE = "sdk"

    def __init__(self, api_url: str, token: str, verify_ssl: bool = True):
        super().__init__(api_url, token)
        self._verify_ssl = verify_ssl

    @lru_cache(maxsize=32)
    def _get_session(self, thread_id, ttl=None):  # noqa
        del ttl
        del thread_id
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[502, 503, 504])

        session = requests.Session()
        session.mount("http://", HTTPAdapter(max_retries=retries))  # noqa
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.headers.update(self.default_headers)
        return session

    def get_session(self):
        return self._get_session(
            thread_id=threading.get_ident(), ttl=round(time.time() / 360)
        )

    @property
    def default_headers(self):
        return {
            "Authorization": self._token,
            "authtype": self.AUTH_TYPE,
            "Content-Type": "application/json",
            "User-Agent": f"Python-SDK-Version: {__version__}; Python: {platform.python_version()};"
            f"OS: {platform.system()}; Team: {self.team_id}",
        }

    @property
    def safe_api(self):
        """
        Context manager which will handle requests calls.
        """

        @contextmanager
        def safe_api():
            """
            Context manager which handles Requests error.
            """
            try:
                yield None
            except (requests.RequestException, ConnectionError) as exc:
                raise AppException(f"Unknown exception: {exc}.")

        return safe_api

    def _request(self, url, method, session, retried=0, **kwargs):

        with self.safe_api():
            req = requests.Request(
                method=method,
                url=url,
                **kwargs,
            )
            prepared = session.prepare_request(req)
            response = session.send(request=prepared, verify=self._verify_ssl)

        if response.status_code == 404 and retried < 3:
            time.sleep(retried * 0.1)
            return self._request(
                url, method=method, session=session, retried=retried + 1, **kwargs
            )
        if response.status_code > 299:
            logger.debug(
                f"Got {response.status_code} response from backend: {response.text}"
            )
        return response

    def _get_url(self, url):
        if not url.startswith("htt"):
            return urllib.parse.urljoin(self._api_url, url)
        return url

    def request(
        self,
        url,
        method="get",
        data=None,
        headers=None,
        params=None,
        retried=0,
        content_type=ServiceResponse,
        files=None,
        dispatcher: str = None,
    ) -> ServiceResponse:
        _url = self._get_url(url)
        kwargs = {"params": {"team_id": self.team_id}}
        if data:
            kwargs["data"] = json.dumps(data, cls=PydanticEncoder)
        if params:
            kwargs["params"].update(params)
        session = self.get_session()
        if files and session.headers.get("Content-Type"):
            del session.headers["Content-Type"]
        session.headers.update(headers if headers else {})
        response = self._request(_url, method, session=session, retried=0, **kwargs)
        if files:
            session.headers.update(self.default_headers)
        return self.serialize_response(response, content_type, dispatcher)

    def paginate(
        self,
        url: str,
        item_type: Any = None,
        chunk_size: int = 2000,
        query_params: Dict[str, Any] = None,
    ) -> ServiceResponse:
        offset = 0
        total = []
        splitter = "&" if "?" in url else "?"

        while True:
            _url = f"{url}{splitter}offset={offset}"
            _response = self.request(
                _url, method="get", params=query_params, dispatcher="data"
            )
            if _response.ok:
                if _response.data:
                    total.extend(_response.data)
                else:
                    break
                data_len = len(_response.data)
                offset += data_len
                if data_len < chunk_size or _response.count - offset < 0:
                    break
            else:
                break

        if item_type:
            response = ServiceResponse(
                status=_response.status,
                res_data=parse_obj_as(List[item_type], total),
            )
        else:
            response = ServiceResponse(
                status=_response.status,
                res_data=total,
            )
        if not _response.ok:
            response.set_error(_response.error)
            response.status = _response.status
        return response

    @staticmethod
    def serialize_response(
        response: requests.Response, content_type, dispatcher: str = None
    ) -> ServiceResponse:
        data = {
            "status": response.status_code,
        }
        try:
            if not response.ok:
                if response.status_code in (502, 504):
                    data[
                        "res_error"
                    ] = "Our service is currently unavailable, please try again later."
                    return content_type(**data)
                else:
                    data_json = response.json()
                    data["res_error"] = data_json.get(
                        "error", data_json.get("errors", "Unknown Error")
                    )
                    return content_type(**data)
            data_json = response.json()
            if dispatcher:
                if dispatcher in data_json:
                    data["res_data"] = data_json.pop(dispatcher)
                else:
                    data["res_data"] = data_json
                    data_json = {}
                data.update(data_json)
            else:
                data["res_data"] = data_json
            return content_type(**data)
        except json.decoder.JSONDecodeError:
            data["res_error"] = response.content
            data["reason"] = response.reason
            return content_type(**data)


class AIOHttpSession(aiohttp.ClientSession):
    RETRY_STATUS_CODES = [401, 403, 502, 503, 504]
    RETRY_LIMIT = 3
    BACKOFF_FACTOR = 0.3

    @staticmethod
    def _copy_form_data(data: aiohttp.FormData) -> aiohttp.FormData:
        form_data = aiohttp.FormData(quote_fields=False)
        for field in data._fields:  # noqa
            if isinstance(field[2], io.IOBase):
                field[2].seek(0)
            form_data.add_field(
                value=field[2],
                content_type=field[1].get("Content-Type", ""),
                **field[0],
            )
        return form_data

    async def request(self, *args, **kwargs) -> aiohttp.ClientResponse:
        attempts = self.RETRY_LIMIT
        delay = 0
        for _ in range(attempts):
            delay += self.BACKOFF_FACTOR
            try:
                response = await super()._request(*args, **kwargs)
                if attempts <= 1 or response.status not in self.RETRY_STATUS_CODES:
                    return response
                if isinstance(kwargs["data"], aiohttp.FormData):
                    raise RuntimeError(await response.text())
            except (aiohttp.ClientError, RuntimeError) as e:
                if attempts <= 1:
                    raise
                data = kwargs["data"]
                if isinstance(data, aiohttp.FormData):
                    kwargs["data"] = self._copy_form_data(data)
            attempts -= 1
            await asyncio.sleep(delay)
