import glob
import json
import logging
from pathlib import Path

import pandas as pd

from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")


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

    project_suffix = "objects.json"
    images = df["imageName"].dropna().unique()
    for image in images:
        image_status = None
        image_pinned = None
        image_height = None
        image_width = None
        image_df = df[df["imageName"] == image]
        image_annotation = {
            "instances": [],
            "metadata": {},
            "tags": [],
            "comments": []
        }
        instances = image_df["instanceId"].dropna().unique()
        for instance in instances:
            instance_df = image_df[image_df["instanceId"] == instance]
            # print(instance_df["instanceId"])
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
            instance_annotation["groupId"] = int(instance_df.iloc[0]["groupId"])
            instance_annotation.update(annotation_meta)
            for _, row in instance_df.iterrows():
                if row["attributeGroupName"] is not None:
                    instance_annotation["attributes"].append(
                        {
                            "groupName": row["attributeGroupName"],
                            "name": row["attributeName"]
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
            "pinned": bool(image_pinned)
        }
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
    include_tags=False,
    verbose=True
):
    """Aggregate annotations as pandas dataframe from project root.

    :param project_root: export path of the project
    :type project_root: Pathlike (str or Path)
    :param include_classes_wo_annotations: enables inclusion of classes info
                                           that have no instances in annotations
    :type include_classes_wo_annotations: bool
    :param include_comments: enables inclusion of comments info as commentResolved column
    :type include_comments: bool
    :param include_tags: enables inclusion of tags info as tag column
    :type include_tags: bool

    :return: DataFrame on annotations with columns: "imageName", "instanceId",
                                                    "className", "attributeGroupName", "attributeName", "type", "error", "locked",
                                                    "visible", "trackingId", "probability", "pointLabels",
                                                    "meta" (geometry information as string), "commentResolved", "classColor",
                                                    "groupId", "imageWidth", "imageHeight", "imageStatus", "imagePinned",
                                                    "createdAt", "creatorRole", "creationType", "creatorEmail", "updatedAt",
                                                    "updatorRole", "updatorEmail", "tag"
    :rtype: pandas DataFrame
    """

    if verbose:
        logger.info(
            "Aggregating annotations from %s as pandas DataFrame", project_root
        )

    annotation_data = {
        "imageName": [],
        "imageHeight": [],
        "imageWidth": [],
        "imageStatus": [],
        "imagePinned": [],
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
        "groupId": [],
        "createdAt": [],
        "creatorRole": [],
        "creationType": [],
        "creatorEmail": [],
        "updatedAt": [],
        "updatorRole": [],
        "updatorEmail": []
    }

    if include_comments:
        annotation_data["commentResolved"] = []
    if include_tags:
        annotation_data["tag"] = []

    classes_path = Path(project_root) / "classes" / "classes.json"
    if not classes_path.is_file():
        raise SABaseException(
            0, "SuperAnnotate classes file " + str(classes_path) +
            " not found. Please provide correct project export root"
        )
    classes_json = json.load(open(classes_path))
    class_name_to_color = {}
    class_group_name_to_values = {}
    for annotation_class in classes_json:
        name = annotation_class["name"]
        color = annotation_class["color"]
        class_name_to_color[name] = color
        class_group_name_to_values[name] = {}
        for attribute_group in annotation_class["attribute_groups"]:
            class_group_name_to_values[name][attribute_group["name"]] = []
            for attribute in attribute_group["attributes"]:
                class_group_name_to_values[name][attribute_group["name"]
                                                ].append(attribute["name"])

    def __append_annotation(annotation_dict):
        for annotation_key in annotation_data:
            if annotation_key in annotation_dict:
                annotation_data[annotation_key].append(
                    annotation_dict[annotation_key]
                )
            else:
                annotation_data[annotation_key].append(None)

    def __get_image_metadata(image_name, annotations):
        image_metadata = {"imageName": image_name}

        image_metadata["imageHeight"] = annotations["metadata"].get("height")
        image_metadata["imageWidth"] = annotations["metadata"].get("width")
        image_metadata["imageStatus"] = annotations["metadata"].get("status")
        image_metadata["imagePinned"] = annotations["metadata"].get("pinned")
        return image_metadata

    def __get_user_metadata(annotation):
        annotation_created_at = pd.to_datetime(annotation.get("createdAt"))
        annotation_created_by = annotation.get("createdBy")
        annotation_creator_email = None
        annotation_creator_role = None
        if annotation_created_by:
            annotation_creator_email = annotation_created_by.get("email")
            annotation_creator_role = annotation_created_by.get("role")
        annotation_creation_type = annotation.get("creationType")
        annotation_updated_at = pd.to_datetime(annotation.get("updatedAt"))
        annotation_updated_by = annotation.get("updatedBy")
        annotation_updator_email = None
        annotation_updator_role = None
        if annotation_updated_by:
            annotation_updator_email = annotation_updated_by.get("email")
            annotation_updator_role = annotation_updated_by.get("role")
        user_metadata = {
            "createdAt": annotation_created_at,
            "creatorRole": annotation_creator_role,
            "creatorEmail": annotation_creator_email,
            "creationType": annotation_creation_type,
            "updatedAt": annotation_updated_at,
            "updatorRole": annotation_updator_role,
            "updatorEmail": annotation_updator_email
        }
        return user_metadata

    annotations_paths = []

    for path in Path(project_root).glob('*.json'):
        annotations_paths.append(path)

    if not annotations_paths:
        logger.warning(
            "No annotations found in project export root %s", project_root
        )
    type_postfix = "___objects.json" if glob.glob(
        "{}/*___objects.json".format(project_root)
    ) else "___pixel.json"
    for annotation_path in annotations_paths:
        annotation_json = json.load(open(annotation_path))
        image_name = annotation_path.name.split(type_postfix)[0]
        image_metadata = __get_image_metadata(image_name, annotation_json)
        annotation_instance_id = 0
        if include_comments:
            for annotation in annotation_json["comments"]:
                comment_resolved = annotation["resolved"]
                comment_meta = {
                    "x": annotation["x"],
                    "y": annotation["y"],
                    "comments": annotation["correspondence"]
                }
                annotation_dict = {
                    "type": "comment",
                    "meta": comment_meta,
                    "commentResolved": comment_resolved,
                }
                user_metadata = __get_user_metadata(annotation)
                annotation_dict.update(user_metadata)
                annotation_dict.update(image_metadata)
                __append_annotation(annotation_dict)
        if include_tags:
            for annotation in annotation_json["tags"]:
                annotation_dict = {"type": "tag", "tag": annotation}
                annotation_dict.update(image_metadata)
                __append_annotation(annotation_dict)
        for annotation in annotation_json["instances"]:
            annotation_type = annotation.get("type", "mask")
            annotation_class_name = annotation.get("className")
            if annotation_class_name is None or annotation_class_name not in class_name_to_color:
                logger.warning(
                    "Annotation class %s not found in classes json. Skipping.",
                    annotation_class_name
                )
                continue
            annotation_class_color = class_name_to_color[annotation_class_name]
            annotation_group_id = annotation.get("groupId")
            annotation_locked = annotation.get("locked")
            annotation_visible = annotation.get("visible")
            annotation_tracking_id = annotation.get("trackingId")
            annotation_meta = None
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
            user_metadata = __get_user_metadata(annotation)
            num_added = 0
            if not attributes:
                annotation_dict = {
                    "imageName": image_name,
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
                    "classColor": annotation_class_color,
                    "groupId": annotation_group_id,
                }
                annotation_dict.update(user_metadata)
                annotation_dict.update(image_metadata)
                __append_annotation(annotation_dict)
                num_added = 1
            else:
                for attribute in attributes:
                    attribute_group = attribute.get("groupName")
                    attribute_name = attribute.get('name')
                    if attribute_group not in class_group_name_to_values[
                        annotation_class_name]:
                        logger.warning(
                            "Annotation class group %s not in classes json. Skipping.",
                            attribute_group
                        )
                        continue
                    if attribute_name not in class_group_name_to_values[
                        annotation_class_name][attribute_group]:
                        logger.warning(
                            "Annotation class group value %s not in classes json. Skipping.",
                            attribute_name
                        )
                        continue
                    annotation_dict = {
                        "imageName": image_name,
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
                        "classColor": annotation_class_color,
                        "groupId": annotation_group_id,
                    }
                    annotation_dict.update(user_metadata)
                    annotation_dict.update(image_metadata)
                    __append_annotation(annotation_dict)
                    num_added += 1

            if num_added > 0:
                annotation_instance_id += 1

    df = pd.DataFrame(annotation_data)

    #Add classes/attributes w/o annotations
    if include_classes_wo_annotations:
        for class_meta in classes_json:
            annotation_class_name = class_meta["name"]
            annotation_class_color = class_meta["color"]

            if not annotation_class_name in df["className"].unique():
                __append_annotation(
                    {
                        "className": annotation_class_name,
                        "classColor": annotation_class_color
                    }
                )
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
                                "classColor": annotation_class_color,
                                "attributeGroupName": attribute_group_name,
                                "attributeName": attribute_name,
                            }
                        )

        df = pd.DataFrame(annotation_data)

    df = df.astype({"probability": float})

    return df
