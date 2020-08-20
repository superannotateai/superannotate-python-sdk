import json
import requests
import requests_toolbelt
import urllib3
import logging

logger = logging.getLogger("annotateonline-python-sdk")

from .version import Version
from .exceptions import SABaseException


class API:
    __instance = None

    def __init__(self):
        if API.__instance is not None:
            raise SABaseException(0, "API class is a singleton!")
        else:
            API.__instance = self

    def set_auth(self, config_location):
        self.api_config = json.load(open(config_location))

        self.token = self.api_config["token"]

        self.default_headers = {'Authorization': self.token}
        if "authtype" in self.api_config:
            self.default_headers["authtype"] = self.api_config["authtype"]
        self.default_headers['User-Agent'] = requests_toolbelt.user_agent(
            'annotateonline', Version
        )

        self.main_endpoint = self.api_config["main_endpoint"]
        self.verify = True
        self.session = None
        response = self.gen_request(req_type='GET', path='/teams')
        if not response.ok:
            if "Not authorized" in response.text:
                raise SABaseException(0, "Couldn't authorize")
            else:
                raise SABaseException(0, "Couldn't reach annotateonline")

    @staticmethod
    def get_instance():
        if API.__instance is None:
            API()
        return API.__instance

    def gen_request(
        self,
        req_type,
        path,
        params=None,
        data=None,
        endpoint='main',
        json_req=None,
        files=None
    ):
        endpoint = self.main_endpoint
        url = endpoint + path

        req = requests.Request(
            method=req_type,
            url=url,
            json=json_req,
            files=files,
            data=data,
            params=params,
            headers=self.default_headers
        )
        prepared = req.prepare()
        return self.send_session(prepared=prepared)

    @staticmethod
    def create_session():
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
        return session

    def send_session(self, prepared):
        if self.session is None:
            self.session = API.create_session()
        resp = self.session.send(
            request=prepared, verify=self.verify, timeout=None
        )

        return resp
