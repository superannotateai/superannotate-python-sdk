from unittest import TestCase

from src.superannotate import SAClient

sa = SAClient()


class CreateProjectFromMetadata(TestCase):
    PROJECT_1 = "pr_1"
    PROJECT_2 = "pr_2"

    def setUp(self) -> None:
        self.tearDown()

    def tearDown(self) -> None:
        for project_name in self.PROJECT_1, self.PROJECT_2:
            try:
                sa.delete_project(project_name)
            except Exception:
                pass

    def test_create_project_with_default_attribute(self):
        sa.create_project(self.PROJECT_1, project_type="Vector", project_description="Desc")
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_1,
            classes_json=[
                {
                    "name": "Personal vehicle",
                    "color": "#ecb65f",
                    "count": 25,
                    "createdAt": "2020-10-12T11:35:20.000Z",
                    "updatedAt": "2020-10-12T11:48:19.000Z",
                    "attribute_groups": [
                        {
                            "name": "test",
                            "attributes": [{"name": "Car"}, {"name": "Track"}, {"name": "Bus"}],
                            "default_value": "Bus"
                        }
                    ]
                }
            ]
        )
        pr_1_metadata = sa.get_project_metadata(self.PROJECT_1, include_annotation_classes=True)
        pr_1_metadata["name"] = self.PROJECT_2
        sa.create_project_from_metadata(pr_1_metadata)
        pr_2_metadata = sa.get_project_metadata(self.PROJECT_2, include_annotation_classes=True)
        assert pr_2_metadata["classes"][0]["attribute_groups"][0]["default_value"] == "Bus"
