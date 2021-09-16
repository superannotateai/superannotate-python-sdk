import json
from pathlib import Path

import pandas as pd
from superannotate.lib.app.mixp.decorators import Trackable


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


@Trackable
def filter_annotation_instances(annotations_df, include=None, exclude=None):
    """Filter annotation instances from project annotations pandas DataFrame.

    include and exclude rules should be a list of rules of the following type:
    [{"className": "<className>", "type" : "<bbox, polygon,...>",
    "error": <True or False>, "attributes" : [{"name" : "<attribute_value>",
    "groupName" : "<attribute_group_name>"},...]},...]


    :param annotations_df: pandas DataFrame of project annotations
    :type annotations_df: pandas.DataFrame
    :param include: include rules
    :type include: list of dicts
    :param exclude: exclude rules
    :type exclude: list of dicts

    :return: filtered DataFrame
    :rtype: pandas.DataFrame

    """
    df = annotations_df.drop(["meta", "pointLabels"], axis=1)

    if include is not None:
        included_dfs = []
        for include_rule in include:
            df_new = df.copy()
            if "className" in include_rule:
                df_new = df_new[df_new["className"] == include_rule["className"]]
            if "attributes" in include_rule:
                for attribute in include_rule["attributes"]:
                    df_new = df_new[
                        (df_new["attributeGroupName"] == attribute["groupName"])
                        & (df_new["attributeName"] == attribute["name"])
                    ]
            if "type" in include_rule:
                df_new = df_new[df_new["type"] == include_rule["type"]]
            if "error" in include_rule:
                df_new = df_new[df_new["error"] == include_rule["error"]]
            included_dfs.append(df_new)

        df = pd.concat(included_dfs)

    if exclude is not None:
        for exclude_rule in exclude:
            df_new = df.copy()
            # with pd.option_context('display.max_rows', None):
            #     print("#", df_new["className"])
            if "className" in exclude_rule:
                df_new = df_new[df_new["className"] == exclude_rule["className"]]
            if "attributes" in exclude_rule:
                for attribute in exclude_rule["attributes"]:
                    df_new = df_new[
                        (df_new["attributeGroup"] == attribute["groupName"])
                        & (df_new["attributeName"] == attribute["name"])
                    ]
            if "type" in exclude_rule:
                df_new = df_new[df_new["type"] == exclude_rule["type"]]
            if "error" in exclude_rule:
                df_new = df_new[df_new["error"] == exclude_rule["error"]]

            df = df.drop(df_new.index)

    result = annotations_df.loc[df.index]
    return result


@Trackable
def filter_images_by_comments(
    annotations_df,
    include_unresolved_comments=True,
    include_resolved_comments=False,
    include_without_comments=False,
):
    """Filter images on comment resolve status and comment existence

    :param annotations_df: pandas DataFrame of project annotations
    :type annotations_df: pandas.DataFrame
    :param include_unresolved_comments: include images with unresolved state
    :type include_unresolved_comments: bool
    :param include_resolved_comments: include images with resolved state
    :type include_resolved_comments: bool
    :param include_without_comments: include images without any comments
    :type include_without_comments: bool

    :return: filtered image names
    :rtype: list of strs

    """
    images = set()
    df = annotations_df[annotations_df["type"] == "comment"]
    if include_unresolved_comments:
        images.update(df[df["commentResolved"] == False]["imageName"].dropna().unique())
    if include_resolved_comments:
        images.update(df[df["commentResolved"] == True]["imageName"].dropna().unique())
    if include_without_comments:
        all_images = set(annotations_df["imageName"].dropna().unique())
        with_comments = set(df["imageName"].dropna().unique())
        images.update(all_images - with_comments)

    return list(images)


@Trackable
def filter_images_by_tags(annotations_df, include=None, exclude=None):
    """Filter images on tags

    :param annotations_df: pandas DataFrame of project annotations
    :type annotations_df: pandas.DataFrame
    :param include: include images with given tags
    :type include: list of strs
    :param exclude: exclude images with given tags
    :type exclude: list of strs

    :return: filtered image names
    :rtype: list of strs

    """

    df = annotations_df[annotations_df["type"] == "tag"]
    images = set(df["imageName"].dropna().unique())

    if include:
        include_images = set(df[df["tag"].isin(include)]["imageName"].dropna().unique())
        images = images.intersection(include_images)

    if exclude:
        exclude_images = set(df[df["tag"].isin(exclude)]["imageName"].dropna().unique())

        images = images.difference(exclude_images)

    return list(images)
