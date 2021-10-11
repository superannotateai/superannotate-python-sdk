from unittest import mock

folder_limit_response = mock.MagicMock()
folder_limit_response.ok = True
folder_limit_response.data.user_limit.remaining_image_count = 0
folder_limit_response.data.project_limit.remaining_image_count = 0
folder_limit_response.data.folder_limit.remaining_image_count = 0


project_limit_response = mock.MagicMock()
project_limit_response.ok = True
project_limit_response.data.user_limit.remaining_image_count = 0
project_limit_response.data.project_limit.remaining_image_count = 0
project_limit_response.data.folder_limit.remaining_image_count = 50000


user_limit_response = mock.MagicMock()
user_limit_response.ok = True
user_limit_response.data.user_limit.remaining_image_count = 0
user_limit_response.data.project_limit.remaining_image_count = 500000
user_limit_response.data.folder_limit.remaining_image_count = 50000
