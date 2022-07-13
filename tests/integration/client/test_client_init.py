# import json
# import os
# import tempfile
# from unittest import TestCase
#
# import superannotate.lib.core as constants
# from superannotate import SAClient
#
#
# class TestClientInit(TestCase):
#     TEST_TOKEN = "test=6085"
#     TEST_URL = "https://test.com"
#
#     def setUp(self) -> None:
#         os.environ.pop('SA_TOKEN', None)
#         os.environ.pop('SA_URL', None)
#         os.environ.pop('SA_SSL', None)
#
#     def test_via_token(self):
#         sa = SAClient(token=self.TEST_TOKEN)
#         assert sa.controller._token == self.TEST_TOKEN
#         assert sa.controller._backend_client.api_url == constants.BACKEND_URL
#
#     def test_via_env_token(self):
#         os.environ.update(
#             {"SA_TOKEN": self.TEST_TOKEN}
#         )
#         sa = SAClient()
#         assert sa.controller._token == self.TEST_TOKEN
#         assert sa.controller._backend_client.api_url == constants.BACKEND_URL
#
#     def test_via_env_vars(self):
#         os.environ.update(
#             {
#                 "SA_TOKEN": self.TEST_TOKEN,
#                 "SA_URL": self.TEST_URL,
#                 "SA_SSL": "False"
#             }
#         )
#         sa = SAClient()
#         assert sa.controller._token == self.TEST_TOKEN
#         assert sa.controller._backend_client.api_url == self.TEST_URL
#         assert sa.controller._backend_client._verify_ssl == False
#
#     def test_via_config_path_with_url_token(self):
#         data = {
#             "token": self.TEST_TOKEN,
#             "main_endpoint": self.TEST_URL,
#             "ssl_verify": True
#         }
#         with tempfile.TemporaryDirectory() as temp_dir:
#             file_path = f"{temp_dir}/config.json"
#             with open(file_path, "w") as file:
#                 json.dump(data, file)
#             sa = SAClient(config_path=file_path)
#             assert sa.controller._token == self.TEST_TOKEN
#             assert sa.controller._backend_client.api_url == self.TEST_URL
#             assert sa.controller._backend_client._verify_ssl == True
#
#     def test_via_config_path_with_token(self):
#         data = {
#             "token": self.TEST_TOKEN,
#         }
#         with tempfile.TemporaryDirectory() as temp_dir:
#             file_path = f"{temp_dir}/config.json"
#             with open(file_path, "w") as file:
#                 json.dump(data, file)
#             sa = SAClient(config_path=file_path)
#             assert sa.controller._token == self.TEST_TOKEN
#             assert sa.controller._backend_client.api_url == constants.BACKEND_URL
#             assert sa.controller._backend_client._verify_ssl == True
