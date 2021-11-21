import json
from pathlib import Path

import pandas as pd
from lib.app.mixp.decorators import Trackable


@Trackable
def df_to_annotations(df, output_dir):
    """Converts and saves pandas DataFrame annotation info (see aggregate_annotations_as_df)
    in output_dir.
    The DataFrame should have columns: "imageName", "className", "attributeGroupName",
    "attributeName", "type", "error", "locked", "visible", trackingId", "probability",
    "pointLabels", "meta", "commentResolved", "classColor", "groupId"

    Currently only works for Vector projects.

    :param df: pandas DataFrame of annotations possibly created by aggregate_annotations_as_df
    :type df: pandas.DataFrame
    :param output_dir: output dir for annotations and classes.json
    :type output_dir: str or Pathlike

    """
    output_dir = Path(output_dir)

    project_suffix = "objects.json"
    images = df["imageName"].dropna().unique()
    for image in images:
        image_status = None
        image_pinned = None
        image_height = None
        image_width = None
        image_df = df[df["imageName"] == image]
        image_annotation = {"instances": [], "metadata": {}, "tags": [], "comments": []}
        instances = image_df["instanceId"].dropna().unique()
        for instance in instances:
            instance_df = image_df[image_df["instanceId"] == instance]
            annotation_type = instance_df.iloc[0]["type"]
            annotation_meta = instance_df.iloc[0]["meta"]

            instance_annotation = {
                "className": instance_df.iloc[0]["className"],
                "type": annotation_type,
                "attributes": [],
                "probability": instance_df.iloc[0]["probability"],
                "error": instance_df.iloc[0]["error"],
            }
            point_labels = instance_df.iloc[0]["pointLabels"]
            if point_labels is None:
                point_labels = []
            instance_annotation["pointLabels"] = point_labels
            instance_annotation["locked"] = bool(instance_df.iloc[0]["locked"])
            instance_annotation["visible"] = bool(instance_df.iloc[0]["visible"])
            instance_annotation["trackingId"] = instance_df.iloc[0]["trackingId"]
            instance_annotation["groupId"] = int(instance_df.iloc[0]["groupId"])
            instance_annotation.update(annotation_meta)
            for _, row in instance_df.iterrows():
                if row["attributeGroupName"] is not None:
                    instance_annotation["attributes"].append(
                        {
                            "groupName": row["attributeGroupName"],
                            "name": row["attributeName"],
                        }
                    )
            image_annotation["instances"].append(instance_annotation)
            image_width = image_width or instance_df.iloc[0]["imageWidth"]
            image_height = image_height or instance_df.iloc[0]["imageHeight"]
            image_pinned = image_pinned or instance_df.iloc[0]["imagePinned"]
            image_status = image_status or instance_df.iloc[0]["imageStatus"]

        comments = image_df[image_df["type"] == "comment"]
        for _, comment in comments.iterrows():
            comment_json = {}
            comment_json.update(comment["meta"])
            comment_json["correspondence"] = comment_json["comments"]
            del comment_json["comments"]
            comment_json["resolved"] = comment["commentResolved"]
            image_annotation["comments"].append(comment_json)

        tags = image_df[image_df["type"] == "tag"]
        for _, tag in tags.iterrows():
            image_annotation["tags"].append(tag["tag"])

        image_annotation["metadata"] = {
            "width": int(image_width),
            "height": int(image_height),
            "status": image_status,
            "pinned": bool(image_pinned),
        }
        json.dump(
            image_annotation,
            open(output_dir / f"{image}___{project_suffix}", "w"),
            indent=4,
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
                    "attribute_groups": [],
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
                {"name": row["attributeGroupName"], "attributes": []}
            )
            attribute_group = annotation_class["attribute_groups"][-1]
        for attribute in attribute_group["attributes"]:
            if attribute["name"] == row["attributeName"]:
                break
        else:
            attribute_group["attributes"].append({"name": row["attributeName"]})

    Path(output_dir / "classes").mkdir(exist_ok=True)
    json.dump(
        annotation_classes, open(output_dir / "classes" / "classes.json", "w"), indent=4
    )
