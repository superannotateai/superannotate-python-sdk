import json
import logging

import requests
import requests_toolbelt
import urllib3

from .exceptions import SABaseException
from .version import Version

logger = logging.getLogger("superannotate-python-sdk")


class API:
    __instance = None

    def __init__(self):
        self.api_config = None
        self.token = None
        self.verify = None
        self.session = None
        self.default_headers = None
        self.main_endpoint = None
        if API.__instance is not None:
            raise SABaseException(0, "API class is a singleton!")
        API.__instance = self

    def set_auth(self, config_location):
        self.api_config = json.load(open(config_location))

        self.token = self.api_config["token"]

        self.default_headers = {'Authorization': self.token}
        self.default_headers["authtype"] = "sdk"
        if "authtype" in self.api_config:
            self.default_headers["authtype"] = self.api_config["authtype"]
        self.default_headers['User-Agent'] = requests_toolbelt.user_agent(
            'superannotate', Version
        )

        self.main_endpoint = "https://api.annotate.online"
        if "main_endpoint" in self.api_config:
            self.main_endpoint = self.api_config["main_endpoint"]
        self.verify = True
        self.session = None
        response = self.send_request(req_type='GET', path='/teams')
        if not response.ok:
            if "Not authorized" in response.text:
                raise SABaseException(0, "Couldn't authorize")
            raise SABaseException(0, "Couldn't reach superannotate")

    @staticmethod
    def get_instance():
        if API.__instance is None:
            API()
        return API.__instance

    def send_request(self, req_type, path, params=None, json_req=None):
        url = self.main_endpoint + path

        req = requests.Request(
            method=req_type, url=url, json=json_req, params=params
        )
        if self.session is None:
            self.session = self._create_session()
        prepared = self.session.prepare_request(req)
        resp = self.session.send(request=prepared, verify=self.verify)
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
        session.headers = self.default_headers
        return session
