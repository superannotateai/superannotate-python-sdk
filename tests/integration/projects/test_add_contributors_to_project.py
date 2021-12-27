# import random
# import string
# from unittest.mock import patch
#
# import src.superannotate as sa
# from src.superannotate import controller
# from src.superannotate.lib.core.entities import TeamEntity
# from src.superannotate.lib.core.entities import ProjectEntity
# from src.superannotate.lib.core.entities import UserEntity
#
# from tests.integration.base import BaseTestCase
#
#
# class TestProject(BaseTestCase):
#     PROJECT_NAME = "add_contributors_to_project"
#     PROJECT_TYPE = "Vector"
#     PROJECT_DESCRIPTION = "DESCRIPTION"
#     TEST_EMAILS = ()
#
#     @property
#     def random_email(self):
#         return f"{''.join(random.choice(string.ascii_letters) for _ in range(7))}@gmail.com"
#
#     @patch("src.superannotate.lib.infrastructure.controller.Controller.get_team")
#     @patch("src.superannotate.lib.infrastructure.controller.Controller.get_project_metadata")
#     def test_add_contributors(self, get_team_mock, get_project_metadata_mock):
#
#         random_emails = [self.random_email for i in range(30)]
#
#         team_users = [UserEntity(email=email) for email in random_emails[: 10]]
#         to_add_emails = random_emails[8: 18]
#         pending_users = random_emails[15: 20]
#         unverified_users = random_emails[20: 30]
#
#         get_team_mock.return_value = TeamEntity(uuid=controller.team_id, users=team_users)
#         get_project_metadata_mock.return_value = dict(
#             data=ProjectEntity(
#                 uuid=controller.team_id,
#                 users=team_users
#             )
#         )
#         # added, skipped = sa.add_contributors_to_project(self.PROJECT_NAME)
