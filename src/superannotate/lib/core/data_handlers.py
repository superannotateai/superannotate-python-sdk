import random
import time
from abc import ABCMeta
from abc import abstractmethod
from collections import defaultdict
from functools import lru_cache
from typing import Any
from typing import Dict
from typing import List

import lib.core as constances
from lib.core.enums import ClassTypeEnum
from lib.core.reporter import Reporter
from superannotate_schemas.schemas.classes import AnnotationClass
from superannotate_schemas.schemas.classes import Attribute
from superannotate_schemas.schemas.classes import AttributeGroup


class BaseDataHandler(metaclass=ABCMeta):
    @abstractmethod
    def handle(self, *args, **kwargs):
        raise NotImplementedError


class ClassIdGenerator:
    def __init__(self):
        self.classes = defaultdict(int)
        self.idx = -1

    def send(self, class_name: str):
        if class_name not in self.classes:
            self.classes[class_name] = self.idx
            self.idx -= 1
        return self.classes[class_name]


class BaseAnnotationDateHandler(BaseDataHandler, metaclass=ABCMeta):
    def __init__(self, annotation_classes: List[AnnotationClass]):
        self._annotation_classes: List[AnnotationClass] = annotation_classes

    @lru_cache()
    def get_annotation_class(self, name: str) -> AnnotationClass:
        for annotation_class in self._annotation_classes:
            if annotation_class.name == name:
                return annotation_class

    @lru_cache()
    def get_attribute_group(
        self, annotation_class: AnnotationClass, attr_group_name: str
    ) -> AttributeGroup:
        for attr_group in annotation_class.attribute_groups:
            if attr_group.name == attr_group_name:
                return attr_group

    @lru_cache()
    def get_attribute(self, attr_group: AttributeGroup, attr_name: str) -> Attribute:
        for attr in attr_group.attributes:
            if attr.name == attr_name:
                return attr


class ChainedAnnotationHandlers:
    def __init__(self):
        self._handlers: List[BaseDataHandler] = list()

    def handle(self, data: Any):
        for handler in self._handlers:
            data = handler.handle(data)
        return data

    def attach(self, handler: BaseDataHandler):
        if handler not in self._handlers:
            self._handlers.append(handler)

    def detach(self, handler):
        if handler in self._handlers:
            self._handlers.remove(handler)

    def detach_all(self):
        self._handlers.clear()


class AnnotationStatusHandler(BaseDataHandler):
    def handle(self, annotations: Dict):
        annotations["metadata"][
            "status"
        ] = constances.AnnotationStatus.IN_PROGRESS.value
        return annotations


class LastActionHandler(BaseDataHandler):
    def __init__(self, email: str):
        self._email = email

    def handle(self, annotations: Dict):
        annotations["metadata"]["lastAction"] = {
            "email": self._email,
            "timestamp": int(time.time()),
        }
        return annotations


class DocumentTagHandler(BaseAnnotationDateHandler):
    def handle(self, annotation: dict):
        new_tags = []
        for tag in annotation["tags"]:
            annotation_class = self.get_annotation_class(tag)
            if annotation_class:
                new_tags.append(annotation_class.id)
        annotation["tags"] = new_tags
        return annotation


class MissingIDsHandler(BaseAnnotationDateHandler):
    def __init__(
        self,
        annotation_classes: List[AnnotationClass],
        templates: List[dict],
        reporter: Reporter,
    ):
        super().__init__(annotation_classes)
        self.validate_existing_classes(annotation_classes)
        self._templates = templates
        self.reporter = reporter

    def validate_existing_classes(self, annotation_classes: List[AnnotationClass]):
        classes_data = defaultdict(dict)
        for annotation_class in annotation_classes:
            class_info = {"id": annotation_class.id, "attribute_groups": {}}
            if annotation_class.attribute_groups:
                for attribute_group in annotation_class.attribute_groups:
                    attribute_group_data = defaultdict(dict)
                    for attribute in attribute_group.attributes:
                        if attribute.name in attribute_group_data.keys():
                            self.reporter.log_warning(
                                f"Duplicate annotation class attribute name {attribute.name}"
                                f" in attribute group {attribute_group.name}. "
                                "Only one of the annotation class attributes will be used. "
                                "This will result in errors in annotation upload."
                            )
                        attribute_group_data[attribute.name] = attribute.id
                    if attribute_group.name in class_info["attribute_groups"].keys():
                        self.reporter.log_warning(
                            f"Duplicate annotation class attribute group name {attribute_group.name}."
                            " Only one of the annotation class attribute groups will be used."
                            " This will result in errors in annotation upload."
                        )
                    class_info["attribute_groups"][attribute_group.name] = {
                        "id": attribute_group.id,
                        "attributes": attribute_group_data,
                    }
            if annotation_class.name in classes_data.keys():
                self.reporter.log_warning(
                    f"Duplicate annotation class name {annotation_class.name}."
                    f" Only one of the annotation classes will be used."
                    " This will result in errors in annotation upload.",
                )

    def _get_class_type(self, annotation_type: str):
        if annotation_type == ClassTypeEnum.TAG.name:
            return ClassTypeEnum.TAG
        return ClassTypeEnum.OBJECT

    def handle(self, annotation: dict):
        if "instances" not in annotation:
            return annotation
        for annotation_instance in annotation["instances"]:
            if "className" not in annotation_instance:
                annotation_instance["classId"] = -1
            else:
                class_name = annotation_instance["className"]
                annotation_class = self.get_annotation_class(class_name)
                if not annotation_class:
                    self.reporter.log_warning(f"Couldn't find class {class_name}")
                    self.reporter.store_message("missing_classes", class_name)
                    annotation_instance["classId"] = -1
                    annotation_instance["attributes"] = []
                    self._annotation_classes.append(
                        AnnotationClass(
                            id=-1,
                            name=class_name,
                            attribute_groups=[],
                            color=f"#{random.randint(0, 0xFFFFFF):06x}",
                        )
                    )
                    self.get_annotation_class.cache_clear()
                else:
                    annotation_instance["classId"] = annotation_class.id

        template_name_id_map = {
            template["name"]: template["id"] for template in self._templates
        }
        for annotation_instance in (
            i for i in annotation["instances"] if i.get("type", None) == "template"
        ):
            annotation_instance["templateId"] = template_name_id_map.get(
                annotation_instance.get("templateName", ""), -1
            )

        for annotation_instance in [
            i for i in annotation["instances"] if "className" in i and i["classId"] > 0
        ]:
            annotation_class_name = annotation_instance["className"]
            annotation_class = self.get_annotation_class(annotation_class_name)

            if not annotation_class:
                self.reporter.log_warning(
                    f"Couldn't find annotation class {annotation_class_name}"
                )
                continue
            annotation_instance_attributes = []
            for annotation_attribute in annotation_instance["attributes"]:
                attr_group = self.get_attribute_group(
                    annotation_class, annotation_attribute["groupName"]
                )
                if not attr_group:
                    self.reporter.log_warning(
                        f"Couldn't find annotation group {annotation_attribute['groupName']}."
                    )
                    self.reporter.store_message(
                        "missing_attribute_groups",
                        f"{annotation_instance['className']}.{annotation_attribute['groupName']}",
                    )
                    continue
                annotation_attribute["groupId"] = attr_group.id
                attribute = self.get_attribute(attr_group, annotation_attribute["name"])
                if not attribute:
                    del annotation_attribute["groupId"]
                    self.reporter.log_warning(
                        f"Couldn't find annotation name {annotation_attribute['name']} in"
                        f" annotation group {annotation_attribute['groupName']}",
                    )
                    self.reporter.store_message(
                        "missing_attributes", annotation_attribute["name"]
                    )
                    continue
                annotation_attribute["id"] = attribute.id
                annotation_instance_attributes.append(annotation_attribute)
            annotation_instance["attributes"] = annotation_instance_attributes
        return annotation


class VideoFormatHandler(BaseAnnotationDateHandler):
    def __init__(self, annotation_classes: List[AnnotationClass], reporter: Reporter):
        super().__init__(annotation_classes)
        self.reporter = reporter

    def handle(self, annotation: dict):
        id_generator = ClassIdGenerator()

        def safe_time(timestamp):
            return "0" if str(timestamp) == "0.0" else timestamp

        def convert_timestamp(timestamp):
            return timestamp / 10 ** 6 if timestamp else "0"

        editor_data = {
            "instances": [],
            "tags": annotation["tags"],
            "name": annotation["metadata"]["name"],
            "metadata": {
                "name": annotation["metadata"]["name"],
                "width": annotation["metadata"].get("width"),
                "height": annotation["metadata"].get("height"),
            },
        }
        if annotation["metadata"].get("duration"):
            editor_data["metadata"]["duration"] = convert_timestamp(
                annotation["metadata"]["duration"]
            )
        for instance in annotation["instances"]:
            meta = instance["meta"]
            class_name = meta.get("className")
            editor_instance = {
                "attributes": [],
                "timeline": {},
                "type": meta["type"],
                "locked": False,
            }
            if class_name:
                annotation_class = self.get_annotation_class(class_name)
                if annotation_class:
                    editor_instance["classId"] = annotation_class.id
                else:
                    editor_instance["classId"] = id_generator.send(class_name)
            else:
                editor_instance["classId"] = id_generator.send("unknown_class")

            if meta.get("pointLabels", None):
                editor_instance["pointLabels"] = meta["pointLabels"]

            active_attributes = set()
            for parameter in instance["parameters"]:

                start_time = safe_time(convert_timestamp(parameter["start"]))
                end_time = safe_time(convert_timestamp(parameter["end"]))

                for timestamp_data in parameter["timestamps"]:
                    timestamp = safe_time(
                        convert_timestamp(timestamp_data["timestamp"])
                    )
                    editor_instance["timeline"][timestamp] = {}

                    if timestamp == start_time:
                        editor_instance["timeline"][timestamp]["active"] = True

                    if timestamp == end_time:
                        editor_instance["timeline"][timestamp]["active"] = False

                    if timestamp_data.get("points", None):
                        editor_instance["timeline"][timestamp][
                            "points"
                        ] = timestamp_data["points"]
                    if not class_name:
                        continue
                    annotation_class = self.get_annotation_class(class_name)
                    if not annotation_class:
                        self.reporter.store_message(
                            "missing_classes", meta["className"]
                        )
                        continue

                    existing_attributes_in_current_instance = set()
                    for attribute in timestamp_data["attributes"]:
                        group_name, attr_name = (
                            attribute.get("groupName"),
                            attribute.get("name"),
                        )
                        attr_group = self.get_attribute_group(
                            annotation_class, group_name
                        )
                        attribute = (
                            self.get_attribute(attr_group, attr_name)
                            if attr_group
                            else None
                        )
                        if not attr_group:
                            self.reporter.store_message(
                                "missing_attribute_groups", f"{class_name}.{group_name}"
                            )
                        elif not attribute:
                            self.reporter.store_message(
                                "missing_attributes",
                                f"{class_name}.{group_name}.{attr_name}",
                            )
                        else:
                            existing_attributes_in_current_instance.add(
                                (group_name, attr_name)
                            )
                    attributes_to_add = (
                        existing_attributes_in_current_instance - active_attributes
                    )
                    attributes_to_delete = (
                        active_attributes - existing_attributes_in_current_instance
                    )
                    if attributes_to_add or attributes_to_delete:
                        editor_instance["timeline"][timestamp][
                            "attributes"
                        ] = defaultdict(list)
                    for new_attribute in attributes_to_add:
                        attribute_group = self.get_attribute_group(
                            annotation_class, new_attribute[0]
                        )
                        attribute = self.get_attribute(
                            attribute_group, new_attribute[1]
                        )
                        attr = {
                            "id": attribute.id,
                            "groupId": attribute_group.id,
                        }
                        active_attributes.add(new_attribute)
                        editor_instance["timeline"][timestamp]["attributes"][
                            "+"
                        ].append(attr)
                    for attribute_to_delete in attributes_to_delete:
                        attribute_group = self.get_attribute_group(
                            annotation_class, attribute_to_delete[0]
                        )
                        attribute = self.get_attribute(
                            attribute_group, attribute_to_delete[1]
                        )
                        attr = {
                            "id": attribute.id,
                            "groupId": attribute_group.id,
                        }
                        active_attributes.remove(attribute_to_delete)
                        editor_instance["timeline"][timestamp]["attributes"][
                            "-"
                        ].append(attr)
            editor_data["instances"].append(editor_instance)
        return editor_data
