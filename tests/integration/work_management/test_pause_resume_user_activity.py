from lib.core.exceptions import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestPauseUserActivity(BaseTestCase):
    PROJECT_NAME = "TestPauseUserActivity"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    ATTACHMENT_LIST = [
        {
            "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
            "name": "6022a74d5384c50017c366b3",
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad",
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad",
        },
    ]

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.ATTACHMENT_LIST)
        users = sa.list_users()
        self.scapegoat = [u for u in users if u["role"] == "Contributor"][0]
        sa.add_contributors_to_project(
            self.PROJECT_NAME, [self.scapegoat["email"]], "QA"
        )

    def test_pause_and_resume_user_activity(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.pause_user_activity(
                pk=self.scapegoat["email"], projects=[self.PROJECT_NAME]
            )
            assert (
                cm.output[0]
                == f"INFO:sa:User with email {self.scapegoat['email']} has been successfully paused"
                f" from the specified projects: {[self.PROJECT_NAME]}."
            )
        with self.assertRaisesRegexp(
            AppException,
            "The user does not have the required permissions for this assignment.",
        ):
            sa.assign_items(
                self.PROJECT_NAME,
                [i["name"] for i in self.ATTACHMENT_LIST],
                self.scapegoat["email"],
            )

        with self.assertLogs("sa", level="INFO") as cm:
            sa.resume_user_activity(
                pk=self.scapegoat["email"], projects=[self.PROJECT_NAME]
            )
            assert (
                cm.output[0]
                == f"INFO:sa:User with email {self.scapegoat['email']} has been successfully unblocked"
                f" from the specified projects: {[self.PROJECT_NAME]}."
            )

        sa.assign_items(
            self.PROJECT_NAME,
            [i["name"] for i in self.ATTACHMENT_LIST],
            self.scapegoat["email"],
        )
