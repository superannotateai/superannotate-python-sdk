import json
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from src.superannotate import AppException
from src.superannotate import SAClient
from src.superannotate.lib.core.entities.classes import ClassTypeEnum
from tests import DATA_SET_PATH

sa = SAClient()


class ProjectCreateBaseTestCase(TestCase):
    PROJECT_NAME = "PROJECT"

    def setUp(self, *args, **kwargs):
        self.tearDown()

    def tearDown(self) -> None:
        try:
            sa.delete_project(self.PROJECT_NAME)
        except AppException:
            ...


class TestCreateMultimodalProject(ProjectCreateBaseTestCase):
    PROJECT_TYPE = "Multimodal"
    PROJECT_NAME = "test_multimodal_create"
    FORM_PATH = DATA_SET_PATH / "multimodal_form" / "form.json"
    EXPECTED_CLASSES = DATA_SET_PATH / "multimodal_form" / "expected_classes.json"

    def test_create_project_with_invalid_form(self):
        """Test project creation with invalid form data"""
        invalid_form = {"invalid": "data"}

        with self.assertRaises(AppException):
            sa.create_project(
                self.PROJECT_NAME,
                "desc",
                self.PROJECT_TYPE,
                form=invalid_form,
            )

    def test_create_project_form_only_multimodal(self):
        """Test that form parameter only works with multimodal projects"""
        with open(self.FORM_PATH) as f:
            form_data = json.load(f)

        # Should work for multimodal
        project = sa.create_project(
            self.PROJECT_NAME,
            "desc",
            "Multimodal",
            form=form_data,
        )
        assert project["type"] == "Multimodal"

    def test_create_project_with_form_classes(self):
        """Test that multimodal project creation with form generates expected classes"""
        with open(self.FORM_PATH) as f:
            form_data = json.load(f)
        sa.create_project(
            self.PROJECT_NAME,
            "desc",
            self.PROJECT_TYPE,
            form=form_data,
        )

        # Get project classes after form attachment
        project_classes = sa.search_annotation_classes(self.PROJECT_NAME)

        # Load expected classes
        with open(self.EXPECTED_CLASSES) as f:
            expected_classes = json.load(f)

        # Compare lengths
        assert len(project_classes) == len(
            expected_classes
        ), f"Expected {len(expected_classes)} classes, got {len(project_classes)}"

        # Sort both lists by name for consistent comparison
        expected_sorted = sorted(expected_classes, key=lambda x: x["name"])
        generated_sorted = sorted(project_classes, key=lambda x: x["name"])

        # Compare each class
        for i, (expected, generated) in enumerate(
            zip(expected_sorted, generated_sorted)
        ):
            # Compare structure (excluding color since it's random and timestamps)
            assert (
                generated["name"] == expected["name"]
            ), f"Class {i}: name mismatch - expected {expected['name']}, got {generated['name']}"

            # todo check
            # assert generated["count"] == expected["count"], \
            #     f"Class {i}: count mismatch"

            assert (
                ClassTypeEnum(expected["type"]).name == generated["type"]
            ), f"Class {i}: type mismatch"

            assert len(generated["attribute_groups"]) == len(
                expected["attribute_groups"]
            ), f"Class {i}: attribute_groups length mismatch"

            # Compare attribute groups
            for j, (exp_group, gen_group) in enumerate(
                zip(expected["attribute_groups"], generated["attribute_groups"])
            ):
                assert (
                    gen_group["name"] == exp_group["name"]
                ), f"Class {i}, group {j}: name mismatch"

                assert (
                    gen_group["group_type"] == exp_group["group_type"]
                ), f"Class {i}, group {j}: group_type mismatch"

                assert len(gen_group["attributes"]) == len(
                    exp_group["attributes"]
                ), f"Class {i}, group {j}: attributes length mismatch"

                # Compare attributes
                for k, (exp_attr, gen_attr) in enumerate(
                    zip(exp_group["attributes"], gen_group["attributes"])
                ):
                    assert (
                        gen_attr["name"] == exp_attr["name"]
                    ), f"Class {i}, group {j}, attr {k}: name mismatch"
                    #  todo check
                    # assert gen_attr["count"] == exp_attr["count"], \
                    #     f"Class {i}, group {j}, attr {k}: count mismatch"
                    assert (
                        gen_attr["default"] == exp_attr["default"]
                    ), f"Class {i}, group {j}, attr {k}: default mismatch"

    def test_create_project_multimodal_no_form(self):
        """Test that multimodal project creation fails when no form is provided"""
        with self.assertRaises(AppException) as context:
            sa.create_project(
                self.PROJECT_NAME,
                "desc",
                self.PROJECT_TYPE,
            )
        assert "A form object is required when creating a Multimodal project." in str(
            context.exception
        )

    def test_create_project_multimodal_with_classes(self):
        """Test that multimodal project creation fails when classes are provided"""
        classes = [
            {
                "type": 1,
                "name": "Test Class",
                "color": "#FF0000",
            }
        ]

        with self.assertRaises(AppException) as context:
            sa.create_project(
                self.PROJECT_NAME,
                "desc",
                self.PROJECT_TYPE,
                classes=classes,
                form={"components": []},
            )
        assert "Classes cannot be provided for Multimodal projects." in str(
            context.exception
        )

    def test_create_project_invalid_form_structure(self):
        """Test project creation with structurally invalid form data"""
        invalid_form = {
            "invalid_key": [
                {"type": "invalid_component", "missing_required_fields": True}
            ]
        }

        with self.assertRaises(AppException):
            sa.create_project(
                self.PROJECT_NAME,
                "desc",
                self.PROJECT_TYPE,
                form=invalid_form,
            )

    def test_create_project_form_attach_failure_cleanup(self):
        """Test that project is deleted when form attachment fails"""
        with open(self.FORM_PATH) as f:
            form_data = json.load(f)

        # Mock the controller to simulate form attachment failure
        with patch.object(
            sa.controller.projects, "attach_form"
        ) as mock_attach_form, patch.object(
            sa.controller.projects, "delete"
        ) as mock_delete:
            # Create a mock response that raises AppException when raise_for_status is called
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = AppException(
                "Form attachment failed"
            )
            mock_attach_form.return_value = mock_response

            # Attempt to create project - should fail and trigger cleanup
            with self.assertRaises(AppException) as context:
                sa.create_project(
                    self.PROJECT_NAME,
                    "desc",
                    self.PROJECT_TYPE,
                    form=form_data,
                )

            # Verify form attachment was attempted
            mock_attach_form.assert_called_once()

            # Verify project deletion was called for cleanup
            mock_delete.assert_called_once()

            # Verify the original exception is re-raised
            assert "Form attachment failed" in str(context.exception)
