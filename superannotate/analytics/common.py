from pathlib import Path
import pandas as pd
import json

import logging
logger = logging.getLogger("superannotate-python-sdk")


def aggregate_annotations_as_df(export_root, project_names):
    """Aggregate annotations as pandas dataframe across multiple projects.
    :param export_root: root export path of the projects
    :type export_root: Pathlike (str or Path)
    :param project_names: list of project names to aggregate through
    :type project_names: list of str
    :return: DataFrame on annotations with columns: ["class", "attribute_group", "attribute_name", "type", "error"] 
    :rtype: pandas DataFrame
    """

    logger.info(
        "Aggregating annotations as pandas dataframe accross projects: {}.".format(
            ' '.join(project_names)
        ),
    )

    annotation_data = {
        "class": [],
        "attribute_group": [],
        "attribute_name": [],
        "type": [],
        "error": []
    }

    for project_name in project_names:
        project_root = Path(export_root).joinpath(project_name)

        annotations_paths = []

        for path in Path(project_root).glob('*.json'):
            if path.name.endswith('___objects.json'
                                 ) or path.name.endswith('___pixel.json'):
                annotations_paths.append(path)

        for annotation_path in annotations_paths:
            annotation_json = json.load(open(annotation_path))

            for annotation in annotation_json:
                if 'className' not in annotation:
                    continue

                class_name = annotation["className"]

                annotation_type = annotation['type'
                                            ] if annotation_path.name.endswith(
                                                '___objects.json'
                                            ) else "mask"
                error = annotation['error'] if 'error' in annotation else None

                attributes = annotation["attributes"]
                if not attributes:

                    annotation_data["class"].append(class_name)
                    annotation_data["attribute_group"].append(None)
                    annotation_data["attribute_name"].append(None)

                    annotation_data["type"].append(annotation_type)
                    annotation_data["error"].append(error)

                for attribute in attributes:

                    attribute_group = attribute["groupName"]
                    attribute_name = attribute['name']

                    annotation_data["class"].append(class_name)

                    annotation_data["attribute_group"].append(attribute_group)
                    annotation_data["attribute_name"].append(attribute_name)

                    annotation_data["type"].append(annotation_type)
                    annotation_data["error"].append(error)

    df = pd.DataFrame(annotation_data)

    return df