import logging

import plotly.express as px
from shapely.geometry import Point, Polygon, box

logger = logging.getLogger("superannotate-python-sdk")


def instance_consensus(inst_1, inst_2):
    """Helper function that computes consensus score between two instances:

    :param inst_1: First instance for consensus score.
    :type inst_1: shapely object
    :param inst_2: Second instance for consensus score.
    :type inst_2: shapely object

    """
    if inst_1.type == inst_2.type == 'Polygon':
        intersect = inst_1.intersection(inst_2)
        union = inst_1.union(inst_2)
        score = intersect.area / union.area
    elif inst_1.type == inst_2.type == 'Point':
        score = -1 * inst_1.distance(inst_2)
    else:
        raise NotImplementedError

    return score


def image_consensus(df, image_name, annot_type):
    """Helper function that computes consensus score for instances of a single image:

    :param df: Annotation data of all images
    :type df: pandas.DataFrame
    :param image_name: The image name for which the consensus score will be computed
    :type image_name: str
    :param annot_type: Type of annotation instances to consider. Available candidates are: ["bbox", "polygon", "point"]
    :type dataset_format: str

    """
    image_df = df[df["imageName"] == image_name]
    all_projects = list(set(df["folderName"]))
    column_names = [
        "creatorEmail", "imageName", "instanceId", "area", "className",
        "attributes", "folderName", "score"
    ]
    instance_id = 0
    image_data = {}
    for column_name in column_names:
        image_data[column_name] = []

    projects_shaply_objs = {}
    # generate shapely objects of instances
    for _, row in image_df.iterrows():
        if row["folderName"] not in projects_shaply_objs:
            projects_shaply_objs[row["folderName"]] = []
        inst_data = row["meta"]
        if annot_type == 'bbox':
            inst_coords = inst_data["points"]
            x1, x2 = inst_coords["x1"], inst_coords["x2"]
            y1, y2 = inst_coords["y1"], inst_coords["y2"]
            inst = box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        elif annot_type == 'polygon':
            inst_coords = inst_data["points"]
            shapely_format = []
            for i in range(0, len(inst_coords) - 1, 2):
                shapely_format.append((inst_coords[i], inst_coords[i + 1]))
            inst = Polygon(shapely_format)
        elif annot_type == 'point':
            inst = Point(inst_data["x"], inst_data["y"])
        if inst.is_valid:
            projects_shaply_objs[row["folderName"]].append(
                (
                    inst, row["className"], row["creatorEmail"],
                    row["attributes"]
                )
            )
        else:
            logger.info(
                "Invalid %s instance occured, skipping to the next one.",
                annot_type
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
            for other_proj, other_proj_instances in projects_shaply_objs.items(
            ):
                if curr_proj == other_proj:
                    max_instances.append((curr_proj, *curr_inst_data))
                    visited_instances[curr_proj][curr_id] = True
                else:
                    if annot_type in ['polygon', 'bbox']:
                        max_score = 0
                    else:
                        max_score = float('-inf')
                    max_inst_data = None
                    max_inst_id = -1
                    for other_id, other_inst_data in enumerate(
                        other_proj_instances
                    ):
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
                image_data["imageName"].append(image_name)
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
                            proj_cons += (1. if score <= 0 else score)
                    image_data["creatorEmail"].append(curr_match_data[3])
                    image_data["attributes"].append(curr_match_data[4])
                    image_data["area"].append(curr_match_data[1].area)
                    image_data["imageName"].append(image_name)
                    image_data["instanceId"].append(instance_id)
                    image_data["className"].append(curr_match_data[2])
                    image_data["folderName"].append(curr_match_data[0])
                    image_data["score"].append(
                        proj_cons / (len(all_projects) - 1)
                    )
            instance_id += 1

    return image_data


def consensus_plot(consensus_df, projects):
    plot_data = consensus_df.copy()

    #annotator-wise boxplot
    annot_box_fig = px.box(
        plot_data,
        x="creatorEmail",
        y="score",
        points="all",
        color="creatorEmail",
        color_discrete_sequence=px.colors.qualitative.Dark24
    )
    annot_box_fig.show()

    #project-wise boxplot
    project_box_fig = px.box(
        plot_data,
        x="folderName",
        y="score",
        points="all",
        color="folderName",
        color_discrete_sequence=px.colors.qualitative.Dark24
    )
    project_box_fig.show()

    #scatter plot of score vs area
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
            "imageName": True,
            "folderName": False,
            "area": False,
            "score": False
        },
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.for_each_trace(lambda t: t.update(name=t.name.split("=")[-1]))
    fig.show()
