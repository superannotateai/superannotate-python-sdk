import json
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
from lib.app.exceptions import AppException


logger = logging.getLogger("sa")


def aggregate_image_annotations_as_df(
    project_root,
    include_classes_wo_annotations=False,
    include_comments=False,
    include_tags=False,
    folder_names=None,
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
    :param folder_names: Aggregate the specified folders from project_root.
                                If None aggregate all folders in the project_root.
    :type folder_names: (list of str)

    :return: DataFrame on annotations with columns:
                                        "itemName", "instanceId",
                                        "className", "attributeGroupName", "attributeName", "type", "error", "locked",
                                        "visible", "trackingId", "probability", "pointLabels",
                                        "meta" (geometry information as string), "commentResolved", "classColor",
                                        "groupId", "imageWidth", "imageHeight", "imageStatus", "imagePinned",
                                        "createdAt", "creatorRole", "creationType", "creatorEmail", "updatedAt",
                                        "updatorRole", "updatorEmail", "tag", "folderName"
    :rtype: pandas DataFrame
    """

    logger.info("Aggregating annotations from %s as pandas DataFrame", project_root)

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
        "updatorEmail": [],
        "folderName": [],
        "imageAnnotator": [],
        "imageQA": [],
    }

    if include_comments:
        annotation_data["commentResolved"] = []
    if include_tags:
        annotation_data["tag"] = []

    classes_path = Path(project_root) / "classes" / "classes.json"
    if not classes_path.is_file():
        raise AppException(
            "SuperAnnotate classes file "
            + str(classes_path)
            + " not found. Please provide correct project export root"
        )
    classes_json = json.load(open(classes_path))
    class_name_to_color = {}
    class_group_name_to_values = {}
    freestyle_attributes = set()
    for annotation_class in classes_json:
        name = annotation_class["name"]
        color = annotation_class["color"]
        class_name_to_color[name] = color
        class_group_name_to_values[name] = {}
        for attribute_group in annotation_class["attribute_groups"]:
            group_type = attribute_group.get("group_type")
            if group_type and group_type in ["text", "numeric"]:
                freestyle_attributes.add(attribute_group["name"])
            class_group_name_to_values[name][attribute_group["name"]] = []
            for attribute in attribute_group["attributes"]:
                class_group_name_to_values[name][attribute_group["name"]].append(
                    attribute["name"]
                )

    def __append_annotation(annotation_dict):
        for annotation_key in annotation_data:
            if annotation_key in annotation_dict:
                annotation_data[annotation_key].append(annotation_dict[annotation_key])
            else:
                annotation_data[annotation_key].append(None)

    def __get_image_metadata(image_name, annotations):
        image_metadata = {"imageName": image_name}

        image_metadata["imageHeight"] = annotations["metadata"].get("height")
        image_metadata["imageWidth"] = annotations["metadata"].get("width")
        image_metadata["imageStatus"] = annotations["metadata"].get("status")
        image_metadata["imagePinned"] = annotations["metadata"].get("pinned")
        image_metadata["imageAnnotator"] = annotations["metadata"].get("annotatorEmail")
        image_metadata["imageQA"] = annotations["metadata"].get("qaEmail")
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
            "updatorEmail": annotation_updator_email,
        }
        return user_metadata

    annotations_paths = []

    if folder_names is None:
        project_dir_content = Path(project_root).glob("*")
        for entry in project_dir_content:
            if entry.is_file() and entry.suffix == ".json":
                annotations_paths.append(entry)
            elif entry.is_dir() and entry.name != "classes":
                annotations_paths.extend(list(entry.rglob("*.json")))
    else:
        for folder_name in folder_names:
            annotations_paths.extend(
                list((Path(project_root) / folder_name).rglob("*.json"))
            )

    if not annotations_paths:
        logger.warning(f"Could not find annotations in {project_root}.")

    if "___objects.json" in annotations_paths[0].name:
        type_postfix = "___objects.json"
    elif "___pixel.json" in annotations_paths[0].name:
        type_postfix = "___pixel.json"
    else:
        type_postfix = ".json"

    for annotation_path in annotations_paths:
        annotation_json = json.load(open(annotation_path))
        parts = annotation_path.name.split(type_postfix)
        if len(parts) != 2:
            continue
        image_name = parts[0]
        image_metadata = __get_image_metadata(image_name, annotation_json)
        annotation_instance_id = 0
        if include_comments:
            for annotation in annotation_json["comments"]:
                comment_resolved = annotation["resolved"]
                comment_meta = {
                    "x": annotation["x"],
                    "y": annotation["y"],
                    "comments": annotation["correspondence"],
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
            if (
                annotation_class_name is None
                or annotation_class_name not in class_name_to_color
            ):
                logger.warning(
                    "Annotation class %s not found in classes json. Skipping.",
                    annotation_class_name,
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
                    "angle": annotation["angle"],
                }
            elif annotation_type == "mask":
                annotation_meta = {"parts": annotation["parts"]}
            elif annotation_type == "template":
                annotation_meta = {
                    "connections": annotation["connections"],
                    "points": annotation["points"],
                }
            annotation_error = annotation.get("error")
            annotation_probability = annotation.get("probability")
            annotation_point_labels = annotation.get("pointLabels")
            attributes = annotation.get("attributes")
            user_metadata = __get_user_metadata(annotation)
            folder_name = None
            if annotation_path.parent != Path(project_root):
                folder_name = annotation_path.parent.name
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
                    "folderName": folder_name,
                }
                annotation_dict.update(user_metadata)
                annotation_dict.update(image_metadata)
                __append_annotation(annotation_dict)
                num_added = 1
            else:
                for attribute in attributes:
                    attribute_group = attribute.get("groupName")
                    attribute_name = attribute.get("name")
                    if (
                        attribute_group
                        not in class_group_name_to_values[annotation_class_name]
                    ):
                        logger.warning(
                            "Annotation class group %s not in classes json. Skipping.",
                            attribute_group,
                        )
                        continue
                    if (
                        attribute_name
                        not in class_group_name_to_values[annotation_class_name][
                            attribute_group
                        ]
                        and attribute_group not in freestyle_attributes
                    ):
                        logger.warning(
                            "Annotation class group value %s not in classes json. Skipping.",
                            attribute_name,
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
                        "folderName": folder_name,
                    }
                    annotation_dict.update(user_metadata)
                    annotation_dict.update(image_metadata)
                    __append_annotation(annotation_dict)
                    num_added += 1

            if num_added > 0:
                annotation_instance_id += 1

    df = pd.DataFrame(annotation_data)

    # Add classes/attributes w/o annotations
    if include_classes_wo_annotations:
        for class_meta in classes_json:
            annotation_class_name = class_meta["name"]
            annotation_class_color = class_meta["color"]

            if annotation_class_name not in df["className"].unique():
                __append_annotation(
                    {
                        "className": annotation_class_name,
                        "classColor": annotation_class_color,
                    }
                )
                continue

            class_df = df[df["className"] == annotation_class_name][
                ["className", "attributeGroupName", "attributeName"]
            ]
            attribute_groups = class_meta["attribute_groups"]

            for attribute_group in attribute_groups:

                attribute_group_name = attribute_group["name"]

                attribute_group_df = class_df[
                    class_df["attributeGroupName"] == attribute_group_name
                ][["attributeGroupName", "attributeName"]]
                attributes = attribute_group["attributes"]
                for attribute in attributes:
                    attribute_name = attribute["name"]

                    if not (
                        attribute_name in attribute_group_df["attributeName"].unique()
                    ):
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


def instance_consensus(inst_1, inst_2):
    """Helper function that computes consensus score between two instances:

    :param inst_1: First instance for consensus score.
    :type inst_1: shapely object or a tag

    :param inst_2: Second instance for consensus score.
    :type inst_2: shapely object or a tag
    """
    if inst_1.type == inst_2.type == "Polygon":
        intersect = inst_1.intersection(inst_2)
        union = inst_1.union(inst_2)
        score = intersect.area / union.area
    elif inst_1.type == inst_2.type == "Point":
        score = -1 * inst_1.distance(inst_2)
    else:
        raise NotImplementedError

    return score


def calculate_tag_consensus(image_df):
    column_names = [
        "creatorEmail",
        "itemName",
        "instanceId",
        "className",
        "folderName",
        "attributeGroupName",
        "attributeName",
    ]

    image_data = {}
    for column_name in column_names:
        image_data[column_name] = []

    image_df = image_df.reset_index()
    image_data["score"] = []
    for i, irow in image_df.iterrows():
        for c in column_names:
            image_data[c].append(irow[c])
        image_data["score"].append(0)
        for j, jrow in image_df.iterrows():
            if i == j:
                continue
            if (
                (irow["className"] == jrow["className"])
                and irow["attributeGroupName"] == jrow["attributeGroupName"]
                and irow["attributeName"] == jrow["attributeName"]
            ):
                image_data["score"][i] += 1
    return image_data


def consensus(df, item_name, annot_type):
    """Helper function that computes consensus score for instances of a single image:

    :param df: Annotation data of all images
    :type df: pandas.DataFrame

    :param image_name: The image name for which the consensus score will be computed
    :type image_name: str

    :param annot_type: Type of annotation instances to consider. Available candidates are: ["bbox", "polygon", "point"]
    :type dataset_format: str
    """

    try:
        from shapely.geometry import Point, Polygon, box
    except ImportError:
        raise ImportError(
            "To use superannotate.consensus function please install shapely package."
        )

    image_df = df[df["itemName"] == item_name]
    all_projects = list(set(df["folderName"]))
    column_names = [
        "creatorEmail",
        "itemName",
        "instanceId",
        "area",
        "className",
        "attributes",
        "folderName",
        "score",
    ]
    instance_id = 0
    image_data = {}
    for column_name in column_names:
        image_data[column_name] = []

    if annot_type == "tag":
        return calculate_tag_consensus(image_df)
    projects_shaply_objs = {}
    # generate shapely objects of instances
    for _, row in image_df.iterrows():
        if row["folderName"] not in projects_shaply_objs:
            projects_shaply_objs[row["folderName"]] = []
        inst_data = row["meta"]
        if annot_type == "bbox":
            inst_coords = inst_data
            x1, x2 = inst_coords["x1"], inst_coords["x2"]
            y1, y2 = inst_coords["y1"], inst_coords["y2"]
            inst = box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        elif annot_type == "polygon":
            inst_coords = inst_data
            shapely_format = []
            for i in range(0, len(inst_coords) - 1, 2):
                shapely_format.append((inst_coords[i], inst_coords[i + 1]))
            inst = Polygon(shapely_format)
        elif annot_type == "point":
            inst = Point(inst_data["x"], inst_data["y"])
        if annot_type != "tag" and inst.is_valid:
            projects_shaply_objs[row["folderName"]].append(
                (inst, row["className"], row["creatorEmail"], row["attributes"])
            )
        else:
            logger.info(
                "Invalid %s instance occured, skipping to the next one.", annot_type
            )
    visited_instances = {}
    for proj, instances in projects_shaply_objs.items():
        visited_instances[proj] = [False] * len(instances)

    # match instances
    for curr_proj, curr_proj_instances in projects_shaply_objs.items():
        for curr_id, curr_inst_data in enumerate(curr_proj_instances):
            curr_inst, curr_class, _, _ = curr_inst_data
            if visited_instances[curr_proj][curr_id] == True:
                continue
            max_instances = []
            for other_proj, other_proj_instances in projects_shaply_objs.items():
                if curr_proj == other_proj:
                    max_instances.append((curr_proj, *curr_inst_data))
                    visited_instances[curr_proj][curr_id] = True
                else:
                    if annot_type in ["polygon", "bbox", "tag"]:
                        max_score = 0
                    else:
                        max_score = float("-inf")
                    max_inst_data = None
                    max_inst_id = -1
                    for other_id, other_inst_data in enumerate(other_proj_instances):
                        other_inst, other_class, _, _ = other_inst_data
                        if visited_instances[other_proj][other_id] == True:
                            continue
                        score = instance_consensus(curr_inst, other_inst)
                        if score > max_score and other_class == curr_class:
                            max_score = score
                            max_inst_data = other_inst_data
                            max_inst_id = other_id
                    if max_inst_data is not None:
                        max_instances.append((other_proj, *max_inst_data))
                        visited_instances[other_proj][max_inst_id] = True
            if len(max_instances) == 1:
                image_data["creatorEmail"].append(max_instances[0][3])
                image_data["attributes"].append(max_instances[0][4])
                image_data["area"].append(max_instances[0][1].area)
                image_data["itemName"].append(item_name)
                image_data["instanceId"].append(instance_id)
                image_data["className"].append(max_instances[0][2])
                image_data["folderName"].append(max_instances[0][0])
                image_data["score"].append(0)
            else:
                for curr_match_data in max_instances:
                    proj_cons = 0
                    for other_match_data in max_instances:
                        if curr_match_data[0] != other_match_data[0]:
                            score = instance_consensus(
                                curr_match_data[1], other_match_data[1]
                            )
                            proj_cons += 1.0 if score <= 0 else score
                    image_data["creatorEmail"].append(curr_match_data[3])
                    image_data["attributes"].append(curr_match_data[4])
                    image_data["area"].append(curr_match_data[1].area)
                    image_data["itemName"].append(item_name)
                    image_data["instanceId"].append(instance_id)
                    image_data["className"].append(curr_match_data[2])
                    image_data["folderName"].append(curr_match_data[0])
                    image_data["score"].append(proj_cons / (len(all_projects) - 1))
            instance_id += 1

    return image_data


def consensus_plot(consensus_df, *_, **__):
    plot_data = consensus_df.copy()

    # annotator-wise boxplot
    annot_box_fig = px.box(
        plot_data,
        x="creatorEmail",
        y="score",
        points="all",
        color="creatorEmail",
        color_discrete_sequence=px.colors.qualitative.Dark24,
    )
    annot_box_fig.show()

    # project-wise boxplot
    project_box_fig = px.box(
        plot_data,
        x="folderName",
        y="score",
        points="all",
        color="folderName",
        color_discrete_sequence=px.colors.qualitative.Dark24,
    )
    project_box_fig.show()

    # scatter plot of score vs area
    fig = px.scatter(
        plot_data,
        x="area",
        y="score",
        color="className",
        symbol="creatorEmail",
        facet_col="folderName",
        color_discrete_sequence=px.colors.qualitative.Dark24,
        hover_data={
            "className": False,
            "itemName": True,
            "folderName": False,
            "area": False,
            "score": False,
        },
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.for_each_trace(lambda t: t.update(name=t.name.split("=")[-1]))
    fig.show()
