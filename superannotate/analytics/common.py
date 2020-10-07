import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger("superannotate-python-sdk")


def aggregate_annotations_as_df(project_root):
    """Aggregate annotations as pandas dataframe from project root.

    :param project_root: export path of the project
    :type project_root: Pathlike (str or Path)

    :return: DataFrame on annotations with columns: ["image_name", class", "attribute_group", "attribute_name", "type", "error", "probability", "point_labels", "meta"]
    :rtype: pandas DataFrame
    """

    logger.info(
        "Aggregating annotations from %s as pandas dataframe", project_root
    )

    annotation_data = {
        "image_name": [],
        "instance_id": [],
        "class": [],
        "attribute_group": [],
        "attribute_name": [],
        "type": [],
        "error": [],
        "probability": [],
        "point_labels": [],
        "meta": []
    }

    def __append_annotation(annotation_dict):
        for annotation_key in annotation_data:
            if annotation_key in annotation_dict:
                annotation_data[annotation_key].append(
                    annotation_dict[annotation_key]
                )
            else:
                annotation_data[annotation_key].append(None)

    annotations_paths = []

    for path in Path(project_root).glob('*.json'):
        if path.name.endswith('___objects.json'
                             ) or path.name.endswith('___pixel.json'):
            annotations_paths.append(path)

    for annotation_path in annotations_paths:
        annotation_json = json.load(open(annotation_path))
        vector = annotation_path.name.endswith('___objects.json')
        annotation_image_name = annotation_path.name.split("___")[0]
        annotation_instance_id = 0
        for annotation in annotation_json:
            if 'className' not in annotation:
                continue
            annotation_instance_id += 1

            annotation_class_name = annotation["className"]

            annotation_type = annotation['type'] if vector else "mask"

            if annotation_type in ["bbox", "polygon", "polyline", "cuboid"]:
                annotation_meta = {"points": annotation["points"]}

            if annotation_type == "point":
                annotation_meta = {"x": annotation["x"], "y": annotation["y"]}
            if annotation_type == "ellipse":
                annotation_meta = {
                    "cx": annotation["cx"],
                    "cy": annotation["cy"],
                    "rx": annotation["rx"],
                    "ry": annotation["ry"],
                    "angle": annotation["angle"]
                }

            if annotation_type == "mask":
                annotation_meta = {"parts": annotation["parts"]}

            annotation_error = annotation['error'
                                         ] if 'error' in annotation else None
            annotation_probability = annotation["probability"]

            annotation_point_labels = annotation["pointLabels"
                                                ] if vector and len(
                                                    annotation["pointLabels"]
                                                ) == 0 else None

            attributes = annotation["attributes"]
            if not attributes:
                __append_annotation(
                    {
                        "image_name": annotation_image_name,
                        "instance_id": annotation_instance_id,
                        "class": annotation_class_name,
                        "type": annotation_type,
                        "mets": annotation_meta,
                        "error": annotation_error,
                        "probability": annotation_probability,
                        "point_labels": annotation_point_labels
                    }
                )

            for attribute in attributes:

                attribute_group = attribute["groupName"]
                attribute_name = attribute['name']

                __append_annotation(
                    {
                        "image_name": annotation_image_name,
                        "instance_id": annotation_instance_id,
                        "class": annotation_class_name,
                        "attribute_group": attribute_group,
                        "attribute_name": attribute_name,
                        "type": annotation_type,
                        "mets": annotation_meta,
                        "error": annotation_error,
                        "probability": annotation_probability,
                        "point_labels": annotation_point_labels
                    }
                )

    df = pd.DataFrame(annotation_data)

    #Add classes/attributes w/o annotations
    classes_json = json.load(
        open(Path(project_root).joinpath("classes/classes.json"))
    )

    for class_meta in classes_json:
        annotation_class_name = class_meta["name"]

        if not annotation_class_name in df["class"].unique():
            __append_annotation({
                "class": annotation_class_name,
            })
            continue

        class_df = df[df["class"] == annotation_class_name][[
            "class", "attribute_group", "attribute_name"
        ]]
        attribute_groups = class_meta["attribute_groups"]

        for attribute_group in attribute_groups:

            attribute_group_name = attribute_group["name"]

            attribute_group_df = class_df[
                class_df["attribute_group"] == attribute_group_name][[
                    "attribute_group", "attribute_name"
                ]]
            attributes = attribute_group["attributes"]
            for attribute in attributes:
                attribute_name = attribute["name"]

                if not attribute_name in attribute_group_df["attribute_name"
                                                           ].unique():
                    __append_annotation(
                        {
                            "class": annotation_class_name,
                            "attribute_group": attribute_group_name,
                            "attribute_name": attribute_name,
                        }
                    )

    df = pd.DataFrame(annotation_data)

    return df
