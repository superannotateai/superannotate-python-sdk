import json
import os
import time
import uuid
from pathlib import Path
from unittest import TestCase

from lib.core.exceptions import AppException
from src.superannotate import SAClient
from tests.integration.work_management.data_set import SCORE_TEMPLATES

sa = SAClient()


class TestUserScoring(TestCase):
    """
    Test using mock Multimodal form template with dynamically generated scores created during setup.
    """

    PROJECT_NAME = "TestUserScoring"
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

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        # setup user scores for test
        cls.tearDownClass()

        cls._project = sa.create_project(
            cls.PROJECT_NAME,
            cls.PROJECT_DESCRIPTION,
            cls.PROJECT_TYPE,
            settings=[{"attribute": "TemplateState", "value": 1}],
            form=cls.MULTIMODAL_FORM,
        )
        team = sa.controller.team
        project = sa.controller.get_project(cls.PROJECT_NAME)
        time.sleep(5)

        # setup form template from crated scores
        with open(cls.EDITOR_TEMPLATE_PATH) as f:
            template_data = json.load(f)
            for data in SCORE_TEMPLATES:
                req = sa.controller.service_provider.work_management.create_score(
                    **data
                )
                assert req.status_code == 201
                for component in template_data["components"]:
                    if "scoring" in component and component["type"] == req.data["type"]:
                        component["scoring"]["id"] = req.data["id"]

            res = sa.controller.service_provider.projects.attach_editor_template(
                team, project, template=template_data
            )
            assert res.ok
        sa.create_annotation_classes_from_classes_json(
            cls.PROJECT_NAME, cls.CLASSES_TEMPLATE_PATH
        )

        users = sa.list_users()
        scapegoat = [
            u for u in users if u["role"] == "Contributor" and u["state"] == "Confirmed"
        ][0]
        cls.scapegoat = scapegoat
        sa.add_contributors_to_project(
            cls.PROJECT_NAME, [scapegoat["email"]], "Annotator"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        # cleanup test scores and project
        projects = sa.search_projects(cls.PROJECT_NAME, return_metadata=True)
        for project in projects:
            try:
                sa.delete_project(project)
            except Exception:
                pass

        score_templates_name_id_map = {
            s.name: s.id
            for s in sa.controller.service_provider.work_management.list_scores().data
        }
        for data in SCORE_TEMPLATES:
            score_id = score_templates_name_id_map.get(data["name"])
            if score_id:
                sa.controller.service_provider.work_management.delete_score(score_id)

    @staticmethod
    def _attach_item(path, name):
        sa.attach_items(path, [{"name": name, "url": "url"}])

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
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=list(scores_name_payload_map.values()),
            )
            assert cm.output[0] == "INFO:sa:Scores successfully set."

        created_scores = sa.get_user_scores(
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

    def test_list_users_with_scores(self):
        # list team users
        team_users = sa.list_users(include=["custom_fields"])
        print(team_users)
        for u in team_users:
            for s in SCORE_TEMPLATES:
                try:
                    assert not u["custom_fields"][f"{s['name']} 7D"]
                    assert not u["custom_fields"][f"{s['name']} 14D"]
                    assert not u["custom_fields"][f"{s['name']} 30D"]
                except KeyError as e:
                    raise AssertionError(str(e))

        # filter team users by score
        filters = {f"custom_field__{SCORE_TEMPLATES[0]['name']} 7D": None}
        team_users = sa.list_users(include=["custom_fields"], **filters)
        assert team_users
        for u in team_users:
            try:
                assert not u["custom_fields"][f"{SCORE_TEMPLATES[0]['name']} 7D"]
            except KeyError as e:
                raise AssertionError(str(e))

        filters = {f"custom_field__{SCORE_TEMPLATES[1]['name']} 30D": 5}
        team_users = sa.list_users(include=["custom_fields"], **filters)
        assert not team_users

    def test_set_get_scores_negative_cases(self):
        item_name = f"test_item_{uuid.uuid4()}"
        self._attach_item(self.PROJECT_NAME, item_name)

        # case when one of wight and value is None
        with self.assertRaisesRegexp(
            AppException, "Weight and Value must both be set or both be None."
        ):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "value": None,
                        "weight": 0.5,
                    }
                ],
            )

        with self.assertRaisesRegexp(
            AppException, "Weight and Value must both be set or both be None."
        ):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_ioc7wd",
                        "value": 5,
                        "weight": None,
                    }
                ],
            )

        # case with invalid keys
        with self.assertRaisesRegexp(AppException, "Invalid Scores."):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "value": 5,
                        "weight": 1.2,
                        "invalid_key": 123,
                    }
                ],
            )

        # case with invalid score name
        with self.assertRaisesRegexp(AppException, "Invalid component_id provided"):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "invalid_component_id",
                        "value": 5,
                        "weight": 0.8,
                    }
                ],
            )

        # case without value key in score
        with self.assertRaisesRegexp(AppException, "Invalid Scores."):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "weight": 1.2,
                    }
                ],
            )

        # case with duplicated acore names
        with self.assertRaisesRegexp(
            AppException, "Component IDs in scores data must be unique."
        ):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "value": 5,
                        "weight": 1.2,
                    },
                    {
                        "component_id": "r_34k7k7",
                        "value": 5,
                        "weight": 1.2,
                    },
                ],
            )

        # case with invalid weight
        with self.assertRaisesRegexp(
            AppException, "Please provide a valid number greater than 0"
        ):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "value": 5,
                        "weight": -1,
                    }
                ],
            )

        # case with invalid scored_user
        with self.assertRaisesRegexp(AppException, "User not found."):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item=item_name,
                scored_user="invalid_email@mail.com",
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "value": 5,
                        "weight": 1,
                    }
                ],
            )

        # case with invalid item
        with self.assertRaisesRegexp(AppException, "Item not found."):
            sa.set_user_scores(
                project=self.PROJECT_NAME,
                item="invalid_item_name",
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "value": 5,
                        "weight": 1,
                    }
                ],
            )

        # case with invalid project
        with self.assertRaisesRegexp(AppException, "Project not found."):
            sa.set_user_scores(
                project="invalid_project_name",
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "value": 5,
                        "weight": 1,
                    }
                ],
            )

        # case with invalid folder
        with self.assertRaisesRegexp(AppException, "Folder not found."):
            sa.set_user_scores(
                project=(self.PROJECT_NAME, "invalid_folder_name"),
                item=item_name,
                scored_user=self.scapegoat["email"],
                scores=[
                    {
                        "component_id": "r_34k7k7",
                        "value": 5,
                        "weight": 1,
                    }
                ],
            )
