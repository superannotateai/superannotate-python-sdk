from typing import Any
from typing import Dict
from typing import List
from typing import Union

from lib.core.exceptions import AppException
from pydantic import BaseModel
from pydantic import Extra


class UserLimits(BaseModel):
    super_user_limit: int
    project_limit: int
    folder_limit: int

    def has_enough_slots(self, count: int):
        if count > self.super_user_limit:
            raise AppException(
                "The number of items you want to upload exceeds the limit of your subscription plan."
            )
        if count > self.project_limit:
            raise AppException(
                "You have exceeded the limit of 500 000 items per project."
            )
        if count > self.folder_limit:
            raise AppException(
                "“You have exceeded the limit of 50 000 items per folder."
            )
        return True


class UploadAnnotationAuthData(BaseModel):
    access_key: str
    secret_key: str
    session_token: str
    region: str
    bucket: str
    images: Dict[int, dict]

    class Config:
        extra = Extra.allow
        fields = {
            "access_key": "accessKeyId",
            "secret_key": "secretAccessKey",
            "session_token": "sessionToken",
            "region": "region",
        }

    def __init__(self, **data):
        credentials = data["creds"]
        data.update(credentials)
        del data["creds"]
        super().__init__(**data)


class DownloadMLModelAuthData(BaseModel):
    access_key: str
    secret_key: str
    session_token: str
    region: str
    bucket: str
    paths: List[str]

    class Config:
        extra = Extra.allow
        fields = {
            "access_key": "accessKeyId",
            "secret_key": "secretAccessKey",
            "session_token": "sessionToken",
            "region": "region",
        }

    def __init__(self, **data):
        credentials = data["tokens"]
        data.update(credentials)
        del data["tokens"]
        super().__init__(**data)


class ServiceResponse(BaseModel):
    status: int
    reason: str
    content: Union[bytes, str]
    data: Any

    def __init__(self, response, content_type):
        data = {
            "status": response.status_code,
            "reason": response.reason,
            "content": response.content,
        }
        if response.ok:
            data["data"] = content_type(**response.json())
        super().__init__(**data)

    @property
    def ok(self):
        return 199 < self.status < 300

    @property
    def error(self):
        return getattr(self.data, "error", "Unknown error.")
