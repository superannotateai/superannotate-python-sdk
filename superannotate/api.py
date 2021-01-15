import os
import json
import logging
from pathlib import Path

import requests
import requests_toolbelt
import urllib3

from .exceptions import SABaseException
from .version import __version__

logger = logging.getLogger("superannotate-python-sdk")


class API:
    __instance = None

    def __init__(self):
        self._api_config = None
        self._token = None
        self._verify = None
        self._session = None
        self._default_headers = None
        self._main_endpoint = None
        self.team_id = None
        if API.__instance is not None:
            raise SABaseException(0, "API class is a singleton!")
        API.__instance = self
        self._authenticated = False

    def init(self, config_location=None):
        if config_location is None:
            config_location = Path.home() / ".superannotate" / "config.json"
            from_none = True
        else:
            config_location = Path(config_location)
            from_none = False

        try:
            if not config_location.is_file():
                raise SABaseException(
                    0, "SuperAnnotate config file " + str(config_location) +
                    " not found. Please provide correct config file location to sa.init(<path>) or use CLI's superannotate init to generate default location config file."
                )
            self._api_config = json.load(open(config_location))

            try:
                self._token = self._api_config["token"]
            except KeyError:
                raise SABaseException(
                    0,
                    "Incorrect config file: 'token' key is not present in the config file "
                    + str(config_location)
                )
            try:
                self.team_id = int(self._token.split("=")[1])
            except Exception:
                raise SABaseException(
                    0,
                    "Incorrect config file: 'token' key is not valid in the config file "
                    + str(config_location)
                )

            self._default_headers = {'Authorization': self._token}
            self._default_headers["authtype"] = "sdk"
            if "authtype" in self._api_config:
                self._default_headers["authtype"] = self._api_config["authtype"]
            self._default_headers['User-Agent'] = requests_toolbelt.user_agent(
                'superannotate', __version__
            )

            self._main_endpoint = "https://api.annotate.online"
            if "main_endpoint" in self._api_config:
                self._main_endpoint = self._api_config["main_endpoint"]
            self._verify = True
            if "ssl_verify" in self._api_config:
                self._verify = self._api_config["ssl_verify"]
            self._session = None
            self._authenticated = True
            response = self.send_request(
                req_type='GET',
                path='/projects',
                params={
                    'team_id': str(self.team_id),
                    'offset': 0,
                    'limit': 1
                }
            )
            if not self._verify:
                urllib3.disable_warnings(
                    urllib3.exceptions.InsecureRequestWarning
                )

            if not response.ok:
                self._authenticated = False
                self._session = None
                if "Not authorized" in response.text:
                    raise SABaseException(
                        0, "Couldn't authorize " + response.text
                    )
                raise SABaseException(
                    0, "Couldn't reach superannotate " + response.text
                )
        except SABaseException:
            self._authenticated = False
            self._session = None
            self.team_id = None
            if not from_none:
                raise

    @staticmethod
    def get_instance():
        if API.__instance is None:
            API()
        return API.__instance

    def send_request(self, req_type, path, params=None, json_req=None):
        if not self._authenticated:
            raise SABaseException(
                0,
                "SuperAnnotate was not initialized. Please provide correct config file location to sa.init(<path>) or use CLI's superannotate init to generate default location config file."
            )
        url = self._main_endpoint + path

        req = requests.Request(
            method=req_type, url=url, json=json_req, params=params
        )
        if self._session is None:
            self._session = self._create_session()
        prepared = self._session.prepare_request(req)
        resp = self._session.send(request=prepared, verify=self._verify)
        return resp

    def _create_session(self):
        session = requests.Session()
        retry = urllib3.Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            # use on any request type
            method_whitelist=False,
            # force retry on those status responses
            status_forcelist=(501, 502, 503, 504, 505, 506, 507, 508, 510, 511),
            raise_on_status=False
        )
        adapter = requests.adapters.HTTPAdapter(
            max_retries=retry, pool_maxsize=16, pool_connections=16
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        session.headers = self._default_headers

        if "SUPERANNOTATE_DEBUG" in os.environ:
            session.hooks['response'].append(_log_requests)

        return session


if "SUPERANNOTATE_DEBUG" in os.environ:
    from requests_toolbelt.utils import dump

    def _log_requests(response, *args, **kwargs):
        data = dump.dump_all(response)
        _log_requests.response_len += len(data)
        logger.info(
            'HTTP %s %s ', response.request.url, _log_requests.response_len
        )

    _log_requests.response_len = 0
