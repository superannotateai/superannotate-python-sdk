import contextlib
from unittest import TestCase

from lib.core.exceptions import AppException
from tests import env


@env.requires_env_vars(env.OWNER_PERSONAL_TOKEN_ENV, env.SA_CONTRIBUTOR_TOKEN_ENV)
class TestAnnotatorToken(TestCase):
    PROJECT_NAME = "TestAnnotatorToken"
    FOREIGN_PROJECT_NAME = "TestTestAnnotatorTokenForeign"
    PROJECT_DESCRIPTION = "annotator token suite"
    PROJECT_TYPE = "Multimodal"
    FOLDER_NAME = "test"

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

    def setUp(self) -> None:
        #: The team owner, who sets the projects up and cleans them up.
        self.owner = env.build_client(env.token(env.OWNER_PERSONAL_TOKEN_ENV))
        #: The client under test: a contributor's key, made project admin below.
        self.annotator = env.build_client(env.token(env.SA_CONTRIBUTOR_TOKEN_ENV))
        #: The user that key acts as - the one the owner promotes.
        self.annotator_email = self.annotator.controller.current_user.email

        self._delete_projects()
        self._project = self.owner.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[
                {"attribute": "TemplateState", "value": 1},
                {"attribute": "CategorizeItems", "value": 2},
                {"attribute": "UploadImages", "value": 1},
                {"attribute": "DeleteImages", "value": 1},
            ],
            form=self.MULTIMODAL_FORM,
        )
        self.owner.create_project(
            self.FOREIGN_PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[
                {"attribute": "TemplateState", "value": 1},
                {"attribute": "CategorizeItems", "value": 2},
            ],
            form=self.MULTIMODAL_FORM,
        )
        added, skipped = self.owner.add_contributors_to_project(
            self.PROJECT_NAME, [self.annotator_email], "Annotator"
        )
        assert self.annotator_email in added + skipped, (
            f"{self.annotator_email} is out of the team scope, so it cannot be made "
            f"a annotator - {env.SA_CONTRIBUTOR_TOKEN_ENV} has to belong to a member "
            f"of the team {env.OWNER_PERSONAL_TOKEN_ENV} owns"
        )

    def tearDown(self) -> None:
        self._delete_projects()

    def _delete_projects(self) -> None:
        for name in (self.PROJECT_NAME, self.FOREIGN_PROJECT_NAME):
            for project in self.owner.list_projects(name=name):
                with contextlib.suppress(Exception):
                    self.owner.delete_project(project["id"])

    def _team_contributor(self):
        """A team contributor for the project admin to add, found as the owner.

        The lookup runs as the owner on purpose: a project-admin key cannot list team
        users (see ``test_lists_team_users``), so it cannot pick its own candidate.
        """
        for user in self.owner.list_users():
            if user["role"] == "Contributor" and user["email"] != self.annotator_email:
                return user
        self.skipTest("the team has no other contributor to add to a project")

    def test_lists_only_the_projects_it_has_access_to(self):
        visible = {p["name"] for p in self.annotator.list_projects()}

        assert self.PROJECT_NAME in visible
        # The second project was never shared, so the role must not surface it.
        assert self.FOREIGN_PROJECT_NAME not in visible
        assert self.FOREIGN_PROJECT_NAME in {
            p["name"] for p in self.owner.list_projects()
        }

    def test_adds_a_contributor_to_its_project(self):
        scapegoat = self._team_contributor()
        with self.assertRaisesRegex(
            AppException, "You do not have sufficient access to share this project."
        ):
            self.annotator.add_contributors_to_project(
                self.PROJECT_NAME, [scapegoat["email"]], "Annotator"
            )

            project_roles = {
                user["email"]: user["role"]
                for user in self.annotator.list_users(project=self.PROJECT_NAME)
            }
            assert project_roles.get(scapegoat["email"]) == "Annotator"

    def test_lists_team_users(self):
        team_users = self.annotator.list_users()

        assert self.annotator_email in {user["email"] for user in team_users}

    def test_lists_the_users_of_its_project(self):
        project_users = self.annotator.list_users(project=self.PROJECT_NAME)

        project_roles = {user["email"]: user["role"] for user in project_users}
        assert project_roles[self.annotator_email] == "Annotator"

    def test_creates_a_folder_in_its_project(self):
        folder = self.annotator.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)

        assert folder["name"] == self.FOLDER_NAME
        assert self.FOLDER_NAME in {
            f["name"] for f in self.annotator.list_folders(self.PROJECT_NAME)
        }

    def test_get_list_delete_items(self):
        self.owner.generate_items(self.PROJECT_NAME, count=5, name="test")

        items = self.annotator.list_items(
            self.PROJECT_NAME, include=["categories", "custom_metadata"]
        )
        item = self.annotator.get_item_metadata(self.PROJECT_NAME, items[0]["name"])
        assert len(items) == 5
        assert item is not None
        self.annotator.delete_items(self.PROJECT_NAME)
        item = self.annotator.get_item_metadata(self.PROJECT_NAME, items[0]["name"])
        assert len(items) == 0

    def test_get_set_annotation(self):
        self.annotator.generate_items(self.PROJECT_NAME, count=5, name="test")
        annotations = self.annotator.get_annotations(
            self.PROJECT_NAME,
        )
        assert len(annotations) == 5
        self.annotator.upload_annotations(self.PROJECT_NAME, annotations)

    def test_get_project_metadata(self):
        self.annotator.get_project_metadata(
            project=self.PROJECT_NAME,
            include_annotation_classes=True,
            include_settings=True,
            # include_workflow=True,
            include_contributors=True,
            include_complete_item_count=True,
        )

    def test_set_item_status(self):
        self.owner.generate_items(self.PROJECT_NAME, count=1, name="test")

        items = self.annotator.list_items(
            self.PROJECT_NAME, include=["categories", "custom_metadata"]
        )
        self.owner.set_annotation_statuses(
            self.PROJECT_NAME, "Completed", [items[0]["name"]]
        )
        items = self.owner.list_items(
            self.PROJECT_NAME, include=["categories", "custom_metadata"]
        )
        assert items[0]["annotation_status"] == "Completed"
