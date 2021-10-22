from collections import defaultdict
from typing import List


def map_annotation_classes_name(annotation_classes, logger=None) -> dict:
    classes_data = defaultdict(dict)
    for annotation_class in annotation_classes:
        class_info = {"id": annotation_class.uuid}
        if annotation_class.attribute_groups:
            for attribute_group in annotation_class.attribute_groups:
                attribute_group_data = defaultdict(dict)
                for attribute in attribute_group["attributes"]:
                    if logger and attribute["name"] in attribute_group_data.keys():
                        logger.warning(
                            f"Duplicate annotation class attribute name {attribute['name']}"
                            f" in attribute group {attribute_group['name']}. "
                            "Only one of the annotation class attributes will be used. "
                            "This will result in errors in annotation upload."
                        )
                    attribute_group_data[attribute["name"]] = attribute["id"]
                if logger and attribute_group["name"] in class_info.keys():
                    logger.warning(
                        f"Duplicate annotation class attribute group name {attribute_group['name']}."
                        " Only one of the annotation class attribute groups will be used."
                        " This will result in errors in annotation upload."
                    )
                class_info["attribute_groups"] = {
                    attribute_group["name"]: {
                        "id": attribute_group["id"],
                        "attributes": attribute_group_data,
                    }
                }
        if logger and annotation_class.name in classes_data.keys():
            logger.warning(
                f"Duplicate annotation class name {annotation_class.name}."
                f" Only one of the annotation classes will be used."
                " This will result in errors in annotation upload.",
            )
        classes_data[annotation_class.name] = class_info
    return classes_data


def fill_annotation_ids(annotations: dict, annotation_classes_name_maps: dict, templates: List[dict], logger=None):
    annotation_classes_name_maps = annotation_classes_name_maps
    if "instances" not in annotations:
        return
    missing_classes = set()
    missing_attribute_groups = set()
    missing_attributes = set()
    unknown_classes = dict()
    report = {
        "missing_classes": missing_classes,
        "missing_attribute_groups": missing_attribute_groups,
        "missing_attributes": missing_attributes,
    }
    for annotation in [i for i in annotations["instances"] if "className" in i]:
        if "className" not in annotation:
            return
        annotation_class_name = annotation["className"]
        if annotation_class_name not in annotation_classes_name_maps.keys():
            if annotation_class_name not in unknown_classes:
                missing_classes.add(annotation_class_name)
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
            if logger:
                logger.warning(
                    f"Couldn't find annotation class {annotation_class_name}"
                )
            continue
        annotation["classId"] = annotation_classes_name_maps[annotation_class_name]["id"]
        for attribute in annotation["attributes"]:
            if (
                    attribute["groupName"]
                    not in annotation_classes_name_maps[annotation_class_name]["attribute_groups"]
            ):
                if logger:
                    logger.warning(
                        f"Couldn't find annotation group {attribute['groupName']}."
                    )
                missing_attribute_groups.add(attribute["groupName"])
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
                if logger:
                    logger.warning(
                        f"Couldn't find annotation name {attribute['name']} in"
                        f" annotation group {attribute['groupName']}",
                    )
                missing_attributes.add(attribute["name"])
                continue
            attribute["id"] = annotation_classes_name_maps[annotation_class_name][
                "attribute_groups"
            ][attribute["groupName"]]["attributes"][attribute["name"]]
    return report
