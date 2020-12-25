import os
import json
import numpy as np

from .sagemaker_helper import _create_classes
from ..sa_json_helper import _create_vector_instance


def sagemaker_object_detection_to_sa_vector(data_path, main_key):
    sa_jsons = {}
    dataset_manifest = []
    try:
        img_map_file = open(data_path / 'output.manifest')
    except Exception as e:
        raise Exception("'output.manifest' file doesn't exist")

    for line in img_map_file:
        dataset_manifest.append(json.loads(line))

    json_list = data_path.glob('*.json')
    classes_ids = {}
    for json_file in json_list:
        data_json = json.load(open(json_file))
        for img in data_json:
            if 'consolidatedAnnotation' not in img.keys():
                print('Wrong json files')
                raise Exception

            manifest = dataset_manifest[int(img['datasetObjectId'])]
            file_name = '%s___objects.json' % os.path.basename(
                manifest['source-ref']
            )

            classes = img['consolidatedAnnotation']['content'][
                main_key + '-metadata']['class-map']
            for key, value in classes.items():
                if key not in classes_ids.keys():
                    classes_ids[key] = value

            annotations = img['consolidatedAnnotation']['content'][main_key][
                'annotations']
            sa_loader = []
            for annotation in annotations:
                points = (
                    annotation['left'], annotation['top'],
                    annotation['left'] + annotation['width'],
                    annotation['top'] + annotation['height']
                )
                sa_obj = _create_vector_instance(
                    'bbox', points, {}, [], classes[str(annotation['class_id'])]
                )
                sa_loader.append(sa_obj.copy())
            sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes(classes_ids)
    return sa_jsons, sa_classes, None
