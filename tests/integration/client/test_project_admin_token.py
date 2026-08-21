"""What a project-admin contributor's API key can do.

The suite runs only when the ``.env`` holds a personal API key of a team contributor
(``SA_PROJECT_ADMIN_TOKEN``); it is skipped otherwise. The setup runs as the team owner
(``SA_OWNER_PERSONAL_TOKEN``) and creates two projects, making that contributor a
ProjectAdmin of one of them - so what the role grants can be told apart from what it
does not. Neither client comes from the suite's own ``SA_TOKEN``: these tests describe
the project-admin key itself, whichever token the rest of the run uses.

Two of them are ``xfail``: a project-admin key cannot list team users, and therefore
cannot add contributors either. Both fail inside the SDK rather than at the backend, see
the reasons on the tests.
"""

import contextlib
from unittest import TestCase

import pytest

from tests import env


@env.requires_tokens(env.OWNER_PERSONAL_TOKEN_ENV, env.SA_CONTRIBUTOR_TOKEN_ENV)
class TestProjectAdminToken(TestCase):
    #: The project the contributor administers.
    PROJECT_NAME = "TestProjectAdminToken"
    #: A project they are never added to, so it has to stay out of their reach.
    FOREIGN_PROJECT_NAME = "TestProjectAdminTokenForeign"
    PROJECT_DESCRIPTION = "project-admin token suite"
    PROJECT_TYPE = "Multimodal"
    FOLDER_NAME = "created-by-project-admin"

    MULTIMODAL_FORM = {
        "components": [
            {
                "id": "r_qx07c6",
                "type": "audio",
                "permissions": [],
                "hasTooltip": False,
                "exclude": False,
                "label": "",
                "value": "",
            }
        ],
        "readme": "",
    }

    @classmethod
    def setUpClass(cls) -> None:
        #: The team owner, who sets the projects up and cleans them up.
        cls.owner = env.build_client(env.token(env.OWNER_PERSONAL_TOKEN_ENV))
        #: The client under test: a contributor's key, made project admin below.
        cls.project_admin = env.build_client(env.token(env.SA_CONTRIBUTOR_TOKEN_ENV))
        #: The user that key acts as - the one the owner promotes.
        cls.project_admin_email = cls.project_admin.controller.current_user.email

        cls._delete_projects()
        cls._project = cls.owner.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE,
            settings=[
                {"attribute": "TemplateState", "value": 1},
                {"attribute": "CategorizeItems", "value": 2},
            ],
            form=cls.MULTIMODAL_FORM
        )
        cls.owner.create_project(
            cls.FOREIGN_PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE,
            settings=[
                {"attribute": "TemplateState", "value": 1},
                {"attribute": "CategorizeItems", "value": 2},
            ],
            form=cls.MULTIMODAL_FORM
        )
        added, skipped = cls.owner.add_contributors_to_project(
            cls.PROJECT_NAME, [cls.project_admin_email], "ProjectAdmin"
        )
        assert cls.project_admin_email in added + skipped, (
            f"{cls.project_admin_email} is out of the team scope, so it cannot be made "
            f"a project admin - {env.SA_CONTRIBUTOR_TOKEN_ENV} has to belong to a member "
            f"of the team {env.OWNER_PERSONAL_TOKEN_ENV} owns"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._delete_projects()

    @classmethod
    def _delete_projects(cls) -> None:
        for name in (cls.PROJECT_NAME, cls.FOREIGN_PROJECT_NAME):
            for project in cls.owner.list_projects(name=name):
                with contextlib.suppress(Exception):
                    cls.owner.delete_project(project["id"])

    def _team_contributor(self):
        """A team contributor for the project admin to add, found as the owner.

        The lookup runs as the owner on purpose: a project-admin key cannot list team
        users (see ``test_lists_team_users``), so it cannot pick its own candidate.
        """
        for user in self.owner.list_users():
            if (
                user["role"] == "Contributor"
                and user["email"] != self.project_admin_email
            ):
                return user
        self.skipTest("the team has no other contributor to add to a project")

    def test_lists_only_the_projects_it_has_access_to(self):
        visible = {p["name"] for p in self.project_admin.list_projects()}

        assert self.PROJECT_NAME in visible
        # The second project was never shared, so the role must not surface it.
        assert self.FOREIGN_PROJECT_NAME not in visible
        assert self.FOREIGN_PROJECT_NAME in {
            p["name"] for p in self.owner.list_projects()
        }

    def test_adds_a_contributor_to_its_project(self):
        scapegoat = self._team_contributor()

        self.project_admin.add_contributors_to_project(
            self.PROJECT_NAME, [scapegoat["email"]], "Annotator"
        )

        project_roles = {
            user["email"]: user["role"]
            for user in self.project_admin.list_users(project=self.PROJECT_NAME)
        }
        assert project_roles.get(scapegoat["email"]) == "Annotator"

    def test_lists_team_users(self):
        team_users = self.project_admin.list_users()

        assert self.project_admin_email in {user["email"] for user in team_users}

    def test_lists_the_users_of_its_project(self):
        project_users = self.project_admin.list_users(project=self.PROJECT_NAME)

        project_roles = {user["email"]: user["role"] for user in project_users}
        assert project_roles[self.project_admin_email] == "ProjectAdmin"

    def test_creates_a_folder_in_its_project(self):
        folder = self.project_admin.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)

        assert folder["name"] == self.FOLDER_NAME
        assert self.FOLDER_NAME in {
            f["name"] for f in self.project_admin.list_folders(self.PROJECT_NAME)
        }

    def test_item_creation(self):
        self.project_admin.generate_items(self.PROJECT_NAME, count=5, name='test')
        items = self.project_admin.list_items(self.PROJECT_NAME)
        assert len(items) == 5
