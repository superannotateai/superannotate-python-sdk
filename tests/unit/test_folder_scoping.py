from unittest import TestCase
from unittest.mock import MagicMock

import pytest

from src.superannotate.lib.core.entities import FolderEntity
from src.superannotate.lib.core.entities import ProjectEntity
from src.superannotate.lib.core.enums import ProjectType
from superannotate import AppException
from src.superannotate.lib.core.usecases.folders import GetFolderUseCase
from src.superannotate.lib.infrastructure.utils import assert_folder_in_project


def _project(project_id=318681, name="P2 13348"):
    return ProjectEntity(
        id=project_id, name=name, team_id=31935, type=ProjectType.MULTIMODAL.value
    )


class TestFolderBelongsToProject(TestCase):
    """A folder resolved for one project must never be handed back for another.

    Folder lookups are scoped by the backend, so a mis-scoped request returns a foreign
    folder rather than an error; everything downstream then addresses it by id, which
    turns the mistake into a silent cross-project write (CUST-1182).
    """

    def test_a_folder_from_another_project_is_rejected(self):
        with pytest.raises(AppException) as exc:
            assert_folder_in_project(
                FolderEntity(id=884408, name="batch1", project_id=318680), _project()
            )

        message = str(exc.value)
        assert "318680" in message and "318681" in message
        assert "batch1" in message

    def test_a_folder_from_the_requested_project_is_accepted(self):
        folder = FolderEntity(id=884500, name="batch1", project_id=318681)

        assert assert_folder_in_project(folder, _project()) is None

    def test_a_response_without_a_project_id_is_not_treated_as_a_mismatch(self):
        # Older backends omit project_id; absence is unknown, not wrong.
        assert (
            assert_folder_in_project(FolderEntity(id=1, name="batch1"), _project())
            is None
        )
        assert assert_folder_in_project(None, _project()) is None


class TestGetFolderUseCaseScoping(TestCase):
    def _use_case(self, returned_folder):
        service_provider = MagicMock()
        service_provider.folders.get_by_name.return_value.data = returned_folder
        return GetFolderUseCase(
            project=_project(),
            service_provider=service_provider,
            folder_name="batch1",
        )

    def test_a_foreign_folder_is_reported_as_an_error_not_returned(self):
        response = self._use_case(
            FolderEntity(id=884408, name="batch1", project_id=318680)
        ).execute()

        assert response.errors
        assert response.data is None

    def test_the_projects_own_folder_is_returned(self):
        folder = FolderEntity(id=884500, name="batch1", project_id=318681)

        response = self._use_case(folder).execute()

        assert not response.errors
        assert response.data is folder
