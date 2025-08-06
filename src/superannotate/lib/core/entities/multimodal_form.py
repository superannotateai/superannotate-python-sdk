"""
Multimodal form validator and class generator for SuperAnnotate projects.

This module provides form validation and automatic class generation for multimodal projects.
It processes form components and generates corresponding annotation classes with proper
attribute groups and default values.

Components that generate classes:
    Text group:
        - audio, avatar, datetime, image, input, code, csv, markdown,
          paragraph, pdf, textarea, time, url, video, web-component

    Number group:
        - number, rating, slider, voting

    Single select group:
        - radio, select (when isMultiselect=False)

    Multiple select group:
        - checkbox, select (when isMultiselect=True)

Components that do not generate classes:
    - button, container, group, divider, grid, tabs

Usage:
    form_model = FormModel(components=form_data['components'])
    classes = form_model.generate_classes()

    # Or use the convenience function
    classes = generate_classes_from_form(form_json)
"""
import random
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel


class BaseComponent(BaseModel):
    id: str
    type: str
    label: Optional[str] = None
    isRequired: Optional[bool] = False
    exclude: Optional[bool] = False


class BaseClassComponent(BaseComponent):
    def generate_class(self):
        raise NotImplementedError()

    @staticmethod
    def _get_random_color():
        """Get random color for class"""
        colors = [
            "#2D1C8F",
            "#F4E1C2",
            "#AC40F2",
            "#FF6B6B",
            "#4ECDC4",
            "#45B7D1",
            "#96CEB4",
            "#FFEAA7",
        ]
        return random.choice(colors)


class SelectComponent(BaseClassComponent):
    options: List[Dict[str, Any]] = []
    isMultiselect: Optional[bool] = False
    isDynamic: Optional[bool] = False

    def generate_class(self):
        """Generate class for select component"""
        # If isDynamic is True, treat as text component
        if self.isDynamic:
            return {
                "name": self.id,
                "color": self._get_random_color(),
                "count": 0,
                "type": 1,
                "attribute_groups": [
                    {"name": f"value_{self.id}", "group_type": "text", "attributes": []}
                ],
            }

        # Normal select behavior
        attributes = []
        default_values = []
        for option in self.options:
            # Check multiple possible fields for default state
            is_default = (
                option.get("checked", False)
                or option.get("selected", False)
                or option.get("default", False)
                or option.get("value") == option.get("defaultValue")
            )
            default_value = 1 if is_default else 0

            option_name = option.get("value", "") or option.get("label", "")
            attributes.append(
                {"name": option_name, "count": 0, "default": default_value}
            )

            if is_default:
                if self.isMultiselect:
                    default_values.append(option_name)
                else:
                    default_values = option_name

        group_type = "checklist" if self.isMultiselect else "radio"
        final_default = (
            default_values
            if self.isMultiselect
            else (default_values if default_values else "")
        )

        return {
            "name": self.id,
            "color": self._get_random_color(),
            "count": 0,
            "type": 1,
            "attribute_groups": [
                {
                    "name": f"value_{self.id}",
                    "group_type": group_type,
                    "attributes": attributes,
                    "default_value": final_default,
                }
            ],
        }


class NumberComponent(BaseClassComponent):
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = 1

    def generate_class(self):
        """Generate class for number component"""
        return {
            "name": self.id,
            "color": self._get_random_color(),
            "count": 0,
            "type": 1,
            "attribute_groups": [
                {"name": f"value_{self.id}", "group_type": "numeric", "attributes": []}
            ],
        }


class TextComponent(BaseClassComponent):
    placeholder: Optional[str] = None
    min: Optional[int] = None
    max: Optional[int] = None

    def generate_class(self):
        """Generate class for text component"""
        return {
            "name": self.id,
            "color": self._get_random_color(),
            "count": 0,
            "type": 1,
            "attribute_groups": [
                {"name": f"value_{self.id}", "group_type": "text", "attributes": []}
            ],
        }


class RadioComponent(BaseClassComponent):
    options: List[Dict[str, Any]] = []

    def generate_class(self):
        """Generate class for radio component"""
        attributes = []
        default_value = ""

        for option in self.options:
            # Check multiple possible fields for default state
            is_default = (
                option.get("checked", False)
                or option.get("selected", False)
                or option.get("default", False)
                or option.get("value") == option.get("defaultValue")
            )
            default_val = 1 if is_default else 0

            option_name = option.get("value", "") or option.get("label", "")
            attributes.append({"name": option_name, "count": 0, "default": default_val})

            if is_default:
                default_value = option_name

        return {
            "name": self.id,
            "color": self._get_random_color(),
            "count": 0,
            "type": 1,
            "attribute_groups": [
                {
                    "name": f"value_{self.id}",
                    "group_type": "radio",
                    "attributes": attributes,
                    "default_value": default_value or "",
                }
            ],
        }


class CheckboxComponent(BaseClassComponent):
    options: List[Dict[str, Any]] = []

    def generate_class(self):
        """Generate class for checkbox component"""
        attributes = []
        default_values = []

        for option in self.options:
            # Check multiple possible fields for default state
            is_default = (
                option.get("checked", False)
                or option.get("selected", False)
                or option.get("default", False)
                or option.get("value") == option.get("defaultValue")
            )
            default_val = 1 if is_default else 0

            option_name = option.get("value", "") or option.get("label", "")
            attributes.append({"name": option_name, "count": 0, "default": default_val})

            if is_default:
                default_values.append(option_name)

        return {
            "name": self.id,
            "color": self._get_random_color(),
            "count": 0,
            "type": 1,
            "attribute_groups": [
                {
                    "name": f"value_{self.id}",
                    "group_type": "checklist",
                    "attributes": attributes,
                    "default_value": default_values,
                }
            ],
        }


class FormModel(BaseModel):
    components: List[Dict[str, Any]]
    code: Optional[Union[str, List]] = ""
    environments: List[Any] = []

    @property
    def code_as_string(self) -> str:
        """Convert code to string if it's a list"""
        if isinstance(self.code, list):
            return "\n".join(str(item) for item in self.code)
        return self.code or ""

    def _extract_all_components(
        self, components: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Recursively extract all components including nested ones"""
        all_components = []

        for component in components:
            # Add current component
            all_components.append(component)

            # Check for children and recursively extract them
            if "children" in component:
                children = component["children"]
                if isinstance(children, list):
                    all_components.extend(self._extract_all_components(children))
                elif isinstance(children, dict):
                    # Handle case where children might be a single component
                    all_components.extend(self._extract_all_components([children]))

        return all_components

    def generate_classes(self) -> List[Dict[str, Any]]:
        """Generate classes from form components"""
        classes = []

        # Component type mappings
        TEXT_COMPONENTS = {
            "audio",
            "avatar",
            "dateTime",
            "image",
            "input",
            "code",
            "csv",
            "markdown",
            "paragraph",
            "pdf",
            "textarea",
            "time",
            "url",
            "video",
            "web-component",
            "webComponent",
            "pdfComponent",
        }

        NUMBER_COMPONENTS = {"number", "rating", "slider", "voting"}

        EXCLUDED_COMPONENTS = {
            "button",
            "container",
            "group",
            "divider",
            "grid",
            "tabs",
        }

        # Extract all components recursively
        all_components = self._extract_all_components(self.components)

        for component_data in all_components:
            component_type = component_data.get("type")

            # Skip excluded components
            if component_type in EXCLUDED_COMPONENTS:
                continue

            # Skip components marked as exclude=True
            if component_data.get("exclude", False):
                continue

            # Create appropriate component instance
            if component_type == "select":
                component = SelectComponent(**component_data)
            elif component_type == "radio":
                component = RadioComponent(**component_data)
            elif component_type == "checkbox":
                component = CheckboxComponent(**component_data)
            elif component_type in NUMBER_COMPONENTS:
                component = NumberComponent(**component_data)
            elif component_type in TEXT_COMPONENTS:
                component = TextComponent(**component_data)
            else:
                # Skip unknown component types
                continue

            # Generate class if component should generate one
            if hasattr(component, "generate_class"):
                class_def = component.generate_class()
                classes.append(class_def)

        return classes


def generate_classes_from_form(form_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate classes JSON from form components.

    Args:
        form_json: Dictionary containing form components

    Returns:
        List of class definitions with attribute groups
    """
    form_model = FormModel(**form_json)
    return form_model.generate_classes()
