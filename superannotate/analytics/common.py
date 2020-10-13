import json
import logging
from pathlib import Path

import pandas as pd
from ..exceptions import SABaseException
logger = logging.getLogger("superannotate-python-sdk")


def df_to_annotations(df, output_dir):
    """Converts and saves pandas DataFrame annotation info (see aggregate_annotations_as_df) in output_dir
    The DataFrame should have columns: "imageName", "classNmae", "attributeGroupName", "attributeName", "type", "error", "locked", "visible", trackingId", "probability", "pointLabels", "meta", "commentResolved", "classColor"

    Currently only works for Vector projects.

    :param df: pandas DataFrame
    :type df: pandas.DataFrame
    :param include_classes_wo_annotations: enables inclusion of classes without annotations info
    :type include_classes_wo_annotations: bool

    :return: DataFrame on annotations with columns: ["imageName", "classNmae", "attributeGroupName", "attributeName", "type", "error", "locked", "visible", trackingId", "probability", "pointLabels", "meta", "commentResolved"]
    :rtype: pandas DataFrame
    """

    project_suffix = "objects.json"
    images = df["imageName"].unique()
    for image in images:
        image_df = df[df["imageName"] == image]
        image_annotation = []
        instances = image_df["instanceId"].unique()
        for instance in instances:
            instance_df = image_df[image_df["instanceId"] == instance]
            annotation_type = instance_df.iloc[0]["type"]
            annotation_meta = instance_df.iloc[0]["meta"]

            instance_annotation = {
                "className": instance_df.iloc[0]["className"],
                "type": annotation_type,
                "attributes": [],
                "probability": instance_df.iloc[0]["probability"],
                "error": instance_df.iloc[0]["error"]
            }
            point_labels = instance_df.iloc[0]["pointLabels"]
            if point_labels is None:
                point_labels = []
            instance_annotation["pointLabels"] = point_labels
            instance_annotation["locked"] = bool(instance_df.iloc[0]["locked"])
            instance_annotation["visible"] = bool(
                instance_df.iloc[0]["visible"]
            )
            instance_annotation["trackingId"] = instance_df.iloc[0]["trackingId"
                                                                   ]
            instance_annotation.update(annotation_meta)
            for _, row in instance_df.iterrows():
                if row["attributeGroupName"] is not None:
                    instance_annotation["attributes"].append(
                        {
                            "groupName": row["attributeGroupName"],
                            "name": row["attributeName"]
                        }
                    )
            image_annotation.append(instance_annotation)
        json.dump(
            image_annotation,
            open(output_dir / f"{image}___{project_suffix}", "w"),
            indent=4
        )

    annotation_classes = []
    for _, row in df.iterrows():
        if row["className"] is None:
            continue
        for annotation_class in annotation_classes:
            if annotation_class["name"] == row["className"]:
                break
        else:
            annotation_classes.append(
                {
                    "name": row["className"],
                    "color": row["classColor"],
                    "attribute_groups": []
                }
            )
            annotation_class = annotation_classes[-1]
        if row["attributeGroupName"] is None or row["attributeName"] is None:
            continue
        for attribute_group in annotation_class["attribute_groups"]:
            if attribute_group["name"] == row["attributeGroupName"]:
                break
        else:
            annotation_class["attribute_groups"].append(
                {
                    "name": row["attributeGroupName"],
                    "attributes": []
                }
            )
            attribute_group = annotation_class["attribute_groups"][-1]
        for attribute in attribute_group["attributes"]:
            if attribute["name"] == row["attributeName"]:
                break
        else:
            attribute_group["attributes"].append({"name": row["attributeName"]})

    Path(output_dir / "classes").mkdir(exist_ok=True)
    json.dump(
        annotation_classes,
        open(output_dir / "classes" / "classes.json", "w"),
        indent=4
    )


def aggregate_annotations_as_df(
    project_root,
    include_classes_wo_annotations=False,
    include_comments=False,
    verbose=True
):
    """Aggregate annotations as pandas dataframe from project root.

    :param project_root: export path of the project
    :type project_root: Pathlike (str or Path)
    :param include_classes_wo_annotations: enables inclusion of classes info that have no instances in annotations
    :type include_classes_wo_annotations: bool
    :param include_comments: enables inclusion of comments info as commentResolved column
    :type include_comments: bool

    :return: DataFrame on annotations with columns: "imageName", "instanceId" className", "attributeGroupName", "attributeName", "type", "error", "locked", "visible", "trackingId", "probability", "pointLabels", "meta" (geometry information as string), "commentResolved", "classColor"
    :rtype: pandas DataFrame
    """

    if verbose:
        logger.info(
            "Aggregating annotations from %s as pandas DataFrame", project_root
        )

    annotation_data = {
        "imageName": [],
        "instanceId": [],
        "className": [],
        "attributeGroupName": [],
        "attributeName": [],
        "type": [],
        "error": [],
        "locked": [],
        "visible": [],
        "trackingId": [],
        "probability": [],
        "pointLabels": [],
        "meta": [],
        "classColor": [],
    }

    if include_comments:
        annotation_data["commentResolved"] = []

    classes_path = Path(project_root) / "classes" / "classes.json"
    if not classes_path.is_file():
        raise SABaseException(
            0, "SuperAnnotate classes file " + str(classes_path) +
            " not found. Please provide correct project export root"
        )
    classes_json = json.load(open(classes_path))

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

    if not annotations_paths:
        logger.warning(
            "No annotations found in project export root %s", project_root
        )

    for annotation_path in annotations_paths:
        annotation_json = json.load(open(annotation_path))
        annotation_image_name = annotation_path.name.split("___")[0]
        annotation_instance_id = 0
        for annotation in annotation_json:
            annotation_class_name = None
            annotation_class_color = None
            attribute_group = None
            attribute_name = None
            annotation_type = None
            annotation_locked = None
            annotation_visible = None
            annotation_tracking_id = None
            annotation_meta = None
            annotation_error = None
            annotation_probability = None
            annotation_point_labels = None
            comment_meta = None
            comment_resolved = None

            annotation_type = annotation.get("type", "mask")

            if annotation_type in ['meta', 'tag']:
                continue

            if annotation_type == "comment":
                if include_comments:
                    comment_resolved = annotation["resolved"]
                    comment_meta = {
                        "x": annotation["x"],
                        "y": annotation["y"],
                        "comments": annotation["comments"]
                    }
                    __append_annotation(
                        {
                            "imageName": annotation_image_name,
                            "type": annotation_type,
                            "meta": comment_meta,
                            "commentResolved": comment_resolved,
                        }
                    )
                continue

            annotation_instance_id += 1

            annotation_class_name = annotation.get("className")
            if annotation_class_name is not None:
                for annotation_class in classes_json:
                    if annotation_class["name"] == annotation_class_name:
                        annotation_class_color = annotation_class["color"]
                        break
                else:
                    raise SABaseException(
                        0, "Annotation class not found in classes.json"
                    )

            annotation_locked = annotation.get("locked")

            annotation_visible = annotation.get("visible")

            annotation_tracking_id = annotation.get("trackingId")

            if annotation_type in ["bbox", "polygon", "polyline", "cuboid"]:
                annotation_meta = {"points": annotation["points"]}
            elif annotation_type == "point":
                annotation_meta = {"x": annotation["x"], "y": annotation["y"]}
            elif annotation_type == "ellipse":
                annotation_meta = {
                    "cx": annotation["cx"],
                    "cy": annotation["cy"],
                    "rx": annotation["rx"],
                    "ry": annotation["ry"],
                    "angle": annotation["angle"]
                }
            elif annotation_type == "mask":
                annotation_meta = {"parts": annotation["parts"]}
            elif annotation_type == "template":
                annotation_meta = {
                    "connections": annotation["connections"],
                    "points": annotation["points"]
                }

            annotation_error = annotation.get('error')

            annotation_probability = annotation.get("probability")

            annotation_point_labels = annotation.get("pointLabels")

            attributes = annotation.get("attributes")

            if not attributes:
                __append_annotation(
                    {
                        "imageName": annotation_image_name,
                        "instanceId": annotation_instance_id,
                        "className": annotation_class_name,
                        "type": annotation_type,
                        "locked": annotation_locked,
                        "visible": annotation_visible,
                        "trackingId": annotation_tracking_id,
                        "meta": annotation_meta,
                        "error": annotation_error,
                        "probability": annotation_probability,
                        "pointLabels": annotation_point_labels,
                        "classColor": annotation_class_color
                    }
                )

            for attribute in attributes:

                attribute_group = attribute["groupName"]
                attribute_name = attribute['name']

                __append_annotation(
                    {
                        "imageName": annotation_image_name,
                        "instanceId": annotation_instance_id,
                        "className": annotation_class_name,
                        "attributeGroupName": attribute_group,
                        "attributeName": attribute_name,
                        "type": annotation_type,
                        "locked": annotation_locked,
                        "visible": annotation_visible,
                        "trackingId": annotation_tracking_id,
                        "meta": annotation_meta,
                        "error": annotation_error,
                        "probability": annotation_probability,
                        "pointLabels": annotation_point_labels,
                        "classColor": annotation_class_color
                    }
                )

    df = pd.DataFrame(annotation_data)

    #Add classes/attributes w/o annotations
    if include_classes_wo_annotations:
        for class_meta in classes_json:
            annotation_class_name = class_meta["name"]

            if not annotation_class_name in df["className"].unique():
                __append_annotation({
                    "className": annotation_class_name,
                })
                continue

            class_df = df[df["className"] == annotation_class_name][[
                "className", "attributeGroupName", "attributeName"
            ]]
            attribute_groups = class_meta["attribute_groups"]

            for attribute_group in attribute_groups:

                attribute_group_name = attribute_group["name"]

                attribute_group_df = class_df[
                    class_df["attributeGroupName"] == attribute_group_name][[
                        "attributeGroupName", "attributeName"
                    ]]
                attributes = attribute_group["attributes"]
                for attribute in attributes:
                    attribute_name = attribute["name"]

                    if not attribute_name in attribute_group_df["attributeName"
                                                               ].unique():
                        __append_annotation(
                            {
                                "className": annotation_class_name,
                                "attributeGroupName": attribute_group_name,
                                "attributeName": attribute_name,
                            }
                        )

        df = pd.DataFrame(annotation_data)

    df = df.astype({"probability": float})

    return df
