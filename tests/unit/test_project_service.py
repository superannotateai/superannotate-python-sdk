from unittest import TestCase
from unittest.mock import MagicMock

from lib.core.entities import ProjectEntity
from lib.infrastructure.services.project import ProjectService


class TestProjectServiceUpdate(TestCase):
    def test_update_does_not_send_priority(self):
        client = MagicMock()
        project = ProjectEntity(
            id=1, name="project", type="Vector", status="InProgress", priority="High"
        )
        ProjectService(client).update(project)
        data = client.request.call_args.kwargs["data"]
        self.assertNotIn("priority", data)
        self.assertEqual(data["name"], "project")
        self.assertEqual(data["status"], 2)
