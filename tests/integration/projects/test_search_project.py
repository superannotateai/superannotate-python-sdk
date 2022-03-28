from unittest import TestCase

import src.superannotate as sa
from src.superannotate.lib.core.entities import ProjectEntity


class TestSearchProject(TestCase):
    PROJECT_1 = "project_1"
    PROJECT_2 = "project_2"

    def setUp(self, *args, **kwargs):
        self.tearDown()

    def tearDown(self) -> None:
        try:
            for project_name in (self.PROJECT_1, self.PROJECT_2):
                projects = sa.search_projects(project_name, return_metadata=True)
                for project in projects:
                    try:
                        sa.delete_project(project)
                    except Exception:
                        pass
        except Exception as e:
            print(str(e))

    @property
    def projects(self):
        return self.PROJECT_2, self.PROJECT_1

    def test_search_by_status(self):
        controller = sa.get_default_controller()

        project_1 = ProjectEntity(
            name=self.PROJECT_1, description="desc", project_type=sa.constances.ProjectType.VECTOR.value,
            status=sa.constances.ProjectStatus.Completed.value, team_id=controller.team_id
        )
        project_2 = ProjectEntity(
            name=self.PROJECT_2, description="desc", project_type=sa.constances.ProjectType.VECTOR.value,
            status=sa.constances.ProjectStatus.InProgress.value, team_id=controller.team_id
        )

        controller.projects.insert(project_1)
        controller.projects.insert(project_2)

        assert self.PROJECT_1 in sa.search_projects(status=sa.constances.ProjectStatus.Completed.name)
        assert self.PROJECT_2 in sa.search_projects(status=sa.constances.ProjectStatus.InProgress.name)

    def test_search_by_multiple_status(self):
        controller = sa.get_default_controller()
        project_1 = ProjectEntity(
            name=self.PROJECT_1, description="desc", project_type=sa.constances.ProjectType.VECTOR.value,
            status=sa.constances.ProjectStatus.OnHold.value, team_id=controller.team_id
        )
        project_2 = ProjectEntity(
            name=self.PROJECT_2, description="desc", project_type=sa.constances.ProjectType.VECTOR.value,
            status=sa.constances.ProjectStatus.OnHold.value, team_id=controller.team_id
        )

        controller.projects.insert(project_1)
        controller.projects.insert(project_2)

        assert all(
            [project in self.projects for project in sa.search_projects(status=sa.constances.ProjectStatus.OnHold.name)]
        )
