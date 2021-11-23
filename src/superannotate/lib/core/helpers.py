import json
import time
from collections import defaultdict
from typing import List

import lib.core as constances
from lib.core.entities import TeamEntity
from lib.core.reporter import Reporter


def map_annotation_classes_name(annotation_classes, reporter: Reporter) -> dict:
    classes_data = defaultdict(dict)
    for annotation_class in annotation_classes:
        class_info = {"id": annotation_class.uuid, "attribute_groups": {}}
        if annotation_class.attribute_groups:
            for attribute_group in annotation_class.attribute_groups:
                attribute_group_data = defaultdict(dict)
                for attribute in attribute_group["attributes"]:
                    if attribute["name"] in attribute_group_data.keys():
                        reporter.log_warning(
                            f"Duplicate annotation class attribute name {attribute['name']}"
                            f" in attribute group {attribute_group['name']}. "
                            "Only one of the annotation class attributes will be used. "
                            "This will result in errors in annotation upload."
                        )
                    attribute_group_data[attribute["name"]] = attribute["id"]
                if attribute_group["name"] in class_info.keys():
                    reporter.log_warning(
                        f"Duplicate annotation class attribute group name {attribute_group['name']}."
                        " Only one of the annotation class attribute groups will be used."
                        " This will result in errors in annotation upload."
                    )
                class_info["attribute_groups"][attribute_group["name"]] = {
                    "id": attribute_group["id"],
                    "attributes": attribute_group_data,
                }

        if annotation_class.name in classes_data.keys():
            reporter.log_warning(
                f"Duplicate annotation class name {annotation_class.name}."
                f" Only one of the annotation classes will be used."
                " This will result in errors in annotation upload.",
            )
        classes_data[annotation_class.name] = class_info
    return classes_data


def fill_document_tags(
    annotations: dict, annotation_classes: dict,
):
    new_tags = []
    for tag in annotations["tags"]:
        if annotation_classes.get(tag):
            new_tags.append(annotation_classes[tag]["id"])
    annotations["tags"] = new_tags


def fill_annotation_ids(
    annotations: dict,
    annotation_classes_name_maps: dict,
    templates: List[dict],
    reporter: Reporter,
):
    annotation_classes_name_maps = annotation_classes_name_maps
    if "instances" not in annotations:
        return
    unknown_classes = dict()

    for annotation in annotations["instances"]:
        if "className" not in annotation:
            annotation["classId"] = -1
        else:
            annotation_class_name = annotation["className"]
            if annotation_class_name not in annotation_classes_name_maps.keys():
                if annotation_class_name not in unknown_classes:
                    reporter.log_warning(f"Couldn't find class {annotation_class_name}")
                    reporter.store_message("missing_classes", annotation_class_name)
                    unknown_classes[annotation_class_name] = {
                        "id": -(len(unknown_classes) + 1),
                        "attribute_groups": {},
                    }
    annotation_classes_name_maps.update(unknown_classes)
    template_name_id_map = {template["name"]: template["id"] for template in templates}
    for annotation in (
        i for i in annotations["instances"] if i.get("type", None) == "template"
    ):
        annotation["templateId"] = template_name_id_map.get(
            annotation.get("templateName", ""), -1
        )

    for annotation in [i for i in annotations["instances"] if "className" in i]:
        annotation_class_name = annotation["className"]
        if annotation_class_name not in annotation_classes_name_maps.keys():
            reporter.log_warning(
                f"Couldn't find annotation class {annotation_class_name}"
            )
            continue
        annotation["classId"] = annotation_classes_name_maps[annotation_class_name][
            "id"
        ]
        for attribute in annotation["attributes"]:
            if (
                attribute["groupName"]
                not in annotation_classes_name_maps[annotation_class_name][
                    "attribute_groups"
                ]
            ):
                reporter.log_warning(
                    f"Couldn't find annotation group {attribute['groupName']}."
                )
                reporter.store_message(
                    "missing_attribute_groups",
                    f"{annotation['className']}.{attribute['groupName']}",
                )
                continue
            attribute["groupId"] = annotation_classes_name_maps[annotation_class_name][
                "attribute_groups"
            ][attribute["groupName"]]["id"]
            if (
                attribute["name"]
                not in annotation_classes_name_maps[annotation_class_name][
                    "attribute_groups"
                ][attribute["groupName"]]["attributes"]
            ):
                del attribute["groupId"]
                reporter.log_warning(
                    f"Couldn't find annotation name {attribute['name']} in"
                    f" annotation group {attribute['groupName']}",
                )
                reporter.store_message("missing_attributes", attribute["name"])
                continue
            attribute["id"] = annotation_classes_name_maps[annotation_class_name][
                "attribute_groups"
            ][attribute["groupName"]]["attributes"][attribute["name"]]


def convert_to_video_editor_json(
    data: dict, class_name_mapper: dict, reporter: Reporter
):
    id_generator = ClassIdGenerator()

    def safe_time(timestamp):
        return "0" if str(timestamp) == "0.0" else timestamp

    def convert_timestamp(timestamp):
        return timestamp / 10 ** 6 if timestamp else "0"

    editor_data = {
        "instances": [],
        "tags": data["tags"],
        "name": data["metadata"]["name"],
        "metadata": {
            "name": data["metadata"]["name"],
            "width": data["metadata"].get("width"),
            "height": data["metadata"].get("height"),
        },
    }
    if data["metadata"].get("duration"):
        editor_data["metadata"]["duration"] = convert_timestamp(
            data["metadata"]["duration"]
        )
    for instance in data["instances"]:
        meta = instance["meta"]
        class_name = meta.get("className")
        editor_instance = {
            "attributes": [],
            "timeline": {},
            "type": meta["type"],
            "locked": False,
        }
        if class_name:
            editor_instance["classId"] = class_name_mapper.get(class_name, {}).get(
                "id", id_generator.send(class_name)
            )
        else:
            editor_instance["classId"] = id_generator.send("unknown_class")
        if meta.get("pointLabels", None):
            editor_instance["pointLabels"] = meta["pointLabels"]
        active_attributes = set()
        for parameter in instance["parameters"]:

            start_time = safe_time(convert_timestamp(parameter["start"]))
            end_time = safe_time(convert_timestamp(parameter["end"]))

            for timestamp_data in parameter["timestamps"]:
                timestamp = safe_time(convert_timestamp(timestamp_data["timestamp"]))
                editor_instance["timeline"][timestamp] = {}

                if timestamp == start_time:
                    editor_instance["timeline"][timestamp]["active"] = True

                if timestamp == end_time:
                    editor_instance["timeline"][timestamp]["active"] = False

                if timestamp_data.get("points", None):
                    editor_instance["timeline"][timestamp]["points"] = timestamp_data[
                        "points"
                    ]
                if not class_name:
                    continue
                elif not class_name_mapper.get(class_name):
                    reporter.store_message("missing_classes", meta["className"])
                    continue

                existing_attributes_in_current_instance = set()
                for attribute in timestamp_data["attributes"]:
                    group_name, attr_name = (
                        attribute.get("groupName"),
                        attribute.get("name"),
                    )
                    if (
                        not class_name_mapper[class_name]
                        .get("attribute_groups", {})
                        .get(group_name)
                    ):
                        reporter.store_message(
                            "missing_attribute_groups", f"{class_name}.{group_name}"
                        )
                    elif (
                        not class_name_mapper[class_name]["attribute_groups"][
                            group_name
                        ]
                        .get("attributes", {})
                        .get(attr_name)
                    ):
                        reporter.store_message(
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
                    editor_instance["timeline"][timestamp]["attributes"] = defaultdict(
                        list
                    )
                for new_attribute in attributes_to_add:
                    attr = {
                        "id": class_name_mapper[class_name]["attribute_groups"][
                            new_attribute[0]
                        ]["attributes"][new_attribute[1]],
                        "groupId": class_name_mapper[class_name]["attribute_groups"][
                            new_attribute[0]
                        ]["id"],
                    }
                    active_attributes.add(new_attribute)
                    editor_instance["timeline"][timestamp]["attributes"]["+"].append(
                        attr
                    )
                for attribute_to_delete in attributes_to_delete:
                    attr = {
                        "id": class_name_mapper[class_name]["attribute_groups"][
                            attribute_to_delete[0]
                        ]["attributes"][attribute_to_delete[1]],
                        "groupId": class_name_mapper[class_name]["attribute_groups"][
                            attribute_to_delete[0]
                        ]["id"],
                    }
                    active_attributes.remove(attribute_to_delete)
                    editor_instance["timeline"][timestamp]["attributes"]["-"].append(
                        attr
                    )
        editor_data["instances"].append(editor_instance)
    return editor_data


def handle_last_action(annotations: dict, team: TeamEntity):
    annotations["metadata"]["lastAction"] = {
        "email": team.creator_id,
        "timestamp": int(time.time()),
    }


def handle_annotation_status(annotations: dict):
    annotations["metadata"]["status"] = constances.AnnotationStatus.IN_PROGRESS.value


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class ClassIdGenerator:
    def __init__(self):
        self.classes = defaultdict(int)
        self.idx = -1

    def send(self, class_name: str):
        if class_name not in self.classes:
            self.classes[class_name] = self.idx
            self.idx -= 1
        return self.classes[class_name]
