from pathlib import Path
import pandas as pd
import json

import logging
logger = logging.getLogger("superannotate-python-sdk")


def aggregate_annotations_as_df(project_root):
    """Aggregate annotations as pandas dataframe from project root.
    :param project_root: export path of the project
    :type project_root: Pathlike (str or Path)
    :return: DataFrame on annotations with columns: ["image_name", class", "attribute_group", "attribute_name", "type", "error", "probability", "point_labels", "meta"] 
    :rtype: pandas DataFrame
    """

    logger.info("Aggregating annotations as pandas dataframe")

    annotation_data = {
        "image_name": [],
        "class": [],
        "attribute_group": [],
        "attribute_name": [],
        "type": [],
        "error": [],
        "probability": [],
        "point_labels": [],
        "meta": []
    }

    annotations_paths = []

    for path in Path(project_root).glob('*.json'):
        if path.name.endswith('___objects.json'
                             ) or path.name.endswith('___pixel.json'):
            annotations_paths.append(path)

    for annotation_path in annotations_paths:
        annotation_json = json.load(open(annotation_path))
        vector = annotation_path.name.endswith('___objects.json')
        annotation_image_name = annotation_path.name.split("___")[0]

        for annotation in annotation_json:
            if 'className' not in annotation:
                continue

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
                                                ] if vector else None

            attributes = annotation["attributes"]
            if not attributes:
                annotation_data["image_name"].append(annotation_image_name)
                annotation_data["class"].append(annotation_class_name)
                annotation_data["attribute_group"].append(None)
                annotation_data["attribute_name"].append(None)
                annotation_data["type"].append(annotation_type)
                annotation_data["meta"].append(annotation_meta)
                annotation_data["error"].append(annotation_error)
                annotation_data["probability"].append(annotation_probability)
                annotation_data["point_labels"].append(annotation_point_labels)

            for attribute in attributes:

                attribute_group = attribute["groupName"]
                attribute_name = attribute['name']

                annotation_data["image_name"].append(annotation_image_name)
                annotation_data["class"].append(annotation_class_name)
                annotation_data["attribute_group"].append(attribute_group)
                annotation_data["attribute_name"].append(attribute_name)
                annotation_data["type"].append(annotation_type)
                annotation_data["meta"].append(annotation_meta)
                annotation_data["error"].append(annotation_error)
                annotation_data["probability"].append(annotation_probability)
                annotation_data["point_labels"].append(annotation_point_labels)

    df = pd.DataFrame(annotation_data)

    return df