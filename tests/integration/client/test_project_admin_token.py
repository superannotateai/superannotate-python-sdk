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
import json
import os
import time
import uuid
from pathlib import Path
from unittest import TestCase

from src.superannotate import AppException
from tests import env
from tests.integration.work_management.data_set import SCORE_TEMPLATES


class BaseProjectAdminTest(TestCase):
    #: The project the contributor administers.
    PROJECT_NAME = "TestProjectAdminToken"
    #: A project they are never added to, so it has to stay out of their reach.
    FOREIGN_PROJECT_NAME = "TestProjectAdminTokenForeign"
    PROJECT_DESCRIPTION = "project-admin token suite"
    PROJECT_TYPE = "Multimodal"
    FOLDER_NAME = "created-by-project-admin"
    SETTINGS = [
        {"attribute": "TemplateState", "value": 1},
        {"attribute": "CategorizeItems", "value": 2},
        {"attribute": "UploadImages", "value": 1},
        {"attribute": "DeleteImages", "value": 1},
    ]
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
        self.project_admin = env.build_client(env.token(env.SA_CONTRIBUTOR_TOKEN_ENV))
        #: The user that key acts as - the one the owner promotes.
        self.project_admin_email = self.project_admin.controller.current_user.email

        self._delete_projects()
        self._project = self.owner.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=self.SETTINGS,
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
            self.PROJECT_NAME, [self.project_admin_email], "ProjectAdmin"
        )
        assert self.project_admin_email in added + skipped, (
            f"{self.project_admin_email} is out of the team scope, so it cannot be made "
            f"a project admin - {env.SA_CONTRIBUTOR_TOKEN_ENV} has to belong to a member "
            f"of the team {env.OWNER_PERSONAL_TOKEN_ENV} owns"
        )

    def tearDown(self) -> None:
        self._delete_projects()

    def _delete_projects(self) -> None:
        for name in (self.PROJECT_NAME, self.FOREIGN_PROJECT_NAME):
            for project in self.owner.list_projects(name=name):
                with contextlib.suppress(Exception):
                    self.owner.delete_project(project["id"])


@env.requires_tokens(env.OWNER_PERSONAL_TOKEN_ENV, env.SA_CONTRIBUTOR_TOKEN_ENV)
class TestProjectAdminTokenFullAccess(BaseProjectAdminTest):
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

    def test_add_remove_a_contributor_to_its_project(self):
        # TODO should raise error on ProjectAdmin deletion
        scapegoat = self._team_contributor()

        self.project_admin.add_contributors_to_project(
            self.PROJECT_NAME, [scapegoat["email"]], "ProjectAdmin"
        )

        project_roles = {
            user["email"]: user["role"]
            for user in self.project_admin.list_users(project=self.PROJECT_NAME)
        }
        assert project_roles.get(scapegoat["email"]) == "ProjectAdmin"
        self.project_admin.remove_users_from_project(
            self.PROJECT_NAME, [scapegoat["email"]]
        )
        project_roles = {
            user["email"]: user["role"]
            for user in self.project_admin.list_users(project=self.PROJECT_NAME)
        }
        assert scapegoat["email"] not in project_roles

    def test_lists_team_users(self):
        team_users = self.project_admin.list_users()

        assert self.project_admin_email in {user["email"] for user in team_users}

    def test_lists_the_users_of_its_project_with_categories(self):
        project_users = self.project_admin.list_users(project=self.PROJECT_NAME)

        project_roles = {user["email"]: user["role"] for user in project_users}
        assert project_roles[self.project_admin_email] == "ProjectAdmin"
        scapegoat = self._team_contributor()

        self.project_admin.add_contributors_to_project(
            self.PROJECT_NAME, [scapegoat["email"]], "Annotator"
        )
        self.project_admin.create_categories(self.PROJECT_NAME, ["test"])
        categories = self.project_admin.list_categories(self.PROJECT_NAME)
        assert len(categories) == 1
        self.project_admin.set_contributors_categories(
            self.PROJECT_NAME, [scapegoat["email"]], categories=["test"]
        )
        users = self.project_admin.list_users(
            project=self.PROJECT_NAME, email=scapegoat["email"], include=["categories"]
        )
        assert users[0]["categories"][0]["name"] == "test"

    def test_creates_a_folder_in_its_project(self):
        folder = self.project_admin.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)

        assert folder["name"] == self.FOLDER_NAME
        assert self.FOLDER_NAME in {
            f["name"] for f in self.project_admin.list_folders(self.PROJECT_NAME)
        }

    def test_get_list_delete_items(self):
        self.project_admin.generate_items(self.PROJECT_NAME, count=5, name="test")

        items = self.project_admin.list_items(
            self.PROJECT_NAME, include=["categories", "custom_metadata"]
        )
        item = self.project_admin.get_item_metadata(self.PROJECT_NAME, items[0]["name"])
        assert len(items) == 5
        assert item is not None
        self.project_admin.delete_items(self.PROJECT_NAME)
        items = self.project_admin.list_items(
            self.PROJECT_NAME, include=["categories", "custom_metadata"]
        )
        assert len(items) == 0

    def test_set_item_status(self):
        self.project_admin.generate_items(self.PROJECT_NAME, count=1, name="test")

        items = self.project_admin.list_items(
            self.PROJECT_NAME, include=["categories", "custom_metadata"]
        )
        self.project_admin.set_annotation_statuses(
            self.PROJECT_NAME, "Completed", [items[0]["name"]]
        )
        items = self.project_admin.list_items(
            self.PROJECT_NAME, include=["categories", "custom_metadata"]
        )
        assert items[0]["annotation_status"] == "Completed"

    def test_get_set_annotation(self):
        self.project_admin.generate_items(self.PROJECT_NAME, count=5, name="test")
        annotations = self.project_admin.get_annotations(
            self.PROJECT_NAME, data_spec="multimodal"
        )
        assert len(annotations) == 5
        response = self.project_admin.upload_annotations(
            self.PROJECT_NAME, annotations, data_spec="multimodal"
        )
        assert len(response["succeeded"]) == 5

    def test_get_project_metadata(self):
        self.project_admin.get_project_metadata(
            project=self.PROJECT_NAME,
            include_annotation_classes=True,
            include_settings=True,
            # include_workflow=True,
            include_contributors=True,
            include_complete_item_count=True,
        )

    def test_delete_project(self):
        # TODO fix project admin should not be able to delete project
        self.project_admin.delete_project(self.PROJECT_NAME)
        projects = self.project_admin.list_projects(name=self.PROJECT_NAME)
        assert not projects


@env.requires_tokens(env.OWNER_PERSONAL_TOKEN_ENV, env.SA_CONTRIBUTOR_TOKEN_ENV)
class TestProjectAdminSemiAccess(BaseProjectAdminTest):
    PROJECT_NAME = "TestProjectAdminSemiAccess"
    FOREIGN_PROJECT_NAME = "TestProjectAdminSemiAccessFOREIGN"
    SETTINGS = [
        {"attribute": "TemplateState", "value": 1},
        {"attribute": "CategorizeItems", "value": 2},
        {"attribute": "UploadImages", "value": 0},
        {"attribute": "DeleteImages", "value": 0},
    ]

    def test_item_deletion(self):
        self.owner.generate_items(self.PROJECT_NAME, count=5, name="test")
        with self.assertRaisesRegex(
            AppException, "You do not have sufficient access to delete this items."
        ):
            self.project_admin.delete_items(self.PROJECT_NAME)

    def test_create_items(self):
        # todo update error message
        with self.assertRaisesRegex(
            AppException, "You do not have sufficient access export."
        ):
            self.project_admin.generate_items(self.PROJECT_NAME, count=5, name="test")


@env.requires_tokens(env.OWNER_PERSONAL_TOKEN_ENV, env.SA_CONTRIBUTOR_TOKEN_ENV)
class TestProjectVectorProject(BaseProjectAdminTest):
    PROJECT_NAME = "TestProjectAdminSemiAccess"
    FOREIGN_PROJECT_NAME = "TestProjectAdminSemiAccessFOREIGN"
    SETTINGS = [
        {"attribute": "TemplateState", "value": 1},
        {"attribute": "CategorizeItems", "value": 2},
        {"attribute": "UploadImages", "value": 0},
        {"attribute": "DeleteImages", "value": 0},
    ]
    PROJECT_TYPE = "Vector"
    MULTIMODAL_FORM = None

    def test_sets_default_image_quality_in_editor(self):
        self.project_admin.set_project_default_image_quality_in_editor(
            self.PROJECT_NAME,
            "original",
        )

        settings = self.project_admin.get_project_settings(self.PROJECT_NAME)
        setting_values = {
            setting["attribute"]: setting["value"] for setting in settings
        }
        assert setting_values["ImageQuality"] == "original", (
            "set_project_default_image_quality_in_editor returned without an error but "
            "left ImageQuality at "
            f"{setting_values['ImageQuality']!r}; the same call as the team owner "
            "applies it, so the Project Admin key is silently ignored"
        )


@env.requires_tokens(env.OWNER_PERSONAL_TOKEN_ENV, env.SA_CONTRIBUTOR_TOKEN_ENV)
class TestProjectAdminUserScoring(TestCase):
    """
    Test using mock Multimodal form template with dynamically generated scores created during setup.
    """

    PROJECT_NAME = "TestProjectAdminUserScoring"
    PROJECT_TYPE = "Multimodal"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    EDITOR_TEMPLATE_PATH = os.path.join(
        Path(__file__).parent.parent.parent,
        "data_set/editor_templates/form_with_scores.json",
    )
    CLASSES_TEMPLATE_PATH = os.path.join(
        Path(__file__).parent.parent.parent,
        "data_set/editor_templates/form1_classes.json",
    )
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

    def setUp(self, *args, **kwargs) -> None:
        # setup user scores for test
        self.owner = env.build_client(env.token(env.OWNER_PERSONAL_TOKEN_ENV))
        self.tearDown()
        #: The client under test: a contributor's key, made project admin below.
        self.project_admin = env.build_client(env.token(env.SA_CONTRIBUTOR_TOKEN_ENV))
        self.project_admin_email = self.project_admin.controller.current_user.email
        self._project = self.owner.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[{"attribute": "TemplateState", "value": 1}],
            form=self.MULTIMODAL_FORM,
        )
        team = self.owner.controller.team
        project = self.owner.controller.get_project(self.PROJECT_NAME)
        self.owner.add_contributors_to_project(
            self.PROJECT_NAME, [self.project_admin_email], "ProjectAdmin"
        )
        time.sleep(5)

        # setup form template from crated scores
        with open(self.EDITOR_TEMPLATE_PATH) as f:
            template_data = json.load(f)
            for data in SCORE_TEMPLATES:
                req = (
                    self.owner.controller.service_provider.work_management.create_score(
                        **data
                    )
                )
                assert req.status_code == 201
                for component in template_data["components"]:
                    if "scoring" in component and component["type"] == req.data["type"]:
                        component["scoring"]["id"] = req.data["id"]

            res = (
                self.owner.controller.service_provider.projects.attach_editor_template(
                    team, project, template=template_data
                )
            )
            assert res.ok
        self.owner.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.CLASSES_TEMPLATE_PATH
        )

        users = self.owner.list_users()
        scapegoat = [
            u for u in users if u["role"] == "Contributor" and u["state"] == "Confirmed"
        ][0]
        self.scapegoat = scapegoat
        self.owner.add_contributors_to_project(
            self.PROJECT_NAME, [scapegoat["email"]], "Annotator"
        )

    def tearDown(self) -> None:
        # cleanup test scores and project
        projects = self.owner.list_projects(name__in=[self.PROJECT_NAME])
        for project in projects:
            try:
                self.owner.delete_project(project=project["id"])
            except Exception as _:
                pass

        score_templates_name_id_map = {
            s.name: s.id
            for s in self.owner.controller.service_provider.work_management.list_scores().data
        }
        for data in SCORE_TEMPLATES:
            score_id = score_templates_name_id_map.get(data["name"])
            if score_id:
                self.owner.controller.service_provider.work_management.delete_score(
                    score_id
                )

    def _attach_item(self, path, name):
        self.owner.attach_items(path, [{"name": name, "url": "url"}])

    def test_set_get_scores(self):
        scores_name_payload_map = {
            "SDK-my-score-1": {
                "component_id": "r_34k7k7",  # rating type score
                "value": 5,
                "weight": 0.5,
            },
            "SDK-my-score-2": {
                "component_id": "r_ioc7wd",  # number type score
                "value": 45,
                "weight": 1.5,
            },
            "SDK-my-score-3": {
                "component_id": "r_tcof7o",  # radio type score
                "value": None,
                "weight": None,
            },
        }
        item_name = f"test_item_{uuid.uuid4()}"
        self._attach_item(self.PROJECT_NAME, item_name)

        with self.assertLogs("sa", level="INFO") as cm:
            self.project_admin.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=list(scores_name_payload_map.values()),
            )
            assert cm.output[0] == "INFO:sa:Scores successfully set."

        created_scores = self.project_admin.get_user_scores(
            project=self.PROJECT_NAME,
            item=item_name,
            scored_user=self.scapegoat["email"],
            score_names=[s["name"] for s in SCORE_TEMPLATES],
        )
        assert len(created_scores) == len(SCORE_TEMPLATES)
        for score in created_scores:
            score_pyload = scores_name_payload_map[score["name"]]
            assert score["value"] == score_pyload["value"]
            assert score["weight"] == score_pyload["weight"]
            assert score["id"]
            assert score["createdAt"]
            assert score["updatedAt"]
