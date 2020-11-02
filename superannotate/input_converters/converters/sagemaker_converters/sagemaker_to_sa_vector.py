import os
import json
from glob import glob
import numpy as np


def _create_classes(classes_map):
    classes_loader = []
    for key, value in classes_map.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {
            'id': int(key),
            'name': value,
            'color': hexcolor,
            'attribute_groups': []
        }
        classes_loader.append(sa_classes)
    return classes_loader


def sagemaker_object_detection_to_sa_vector(data_path, main_key):
    sa_jsons = {}
    dataset_manifest = []
    try:
        img_map_file = open(os.path.join(data_path, 'output.manifest'))
    except Exception as e:
        raise Exception("'output.manifest' file doesn't exist")

    for line in img_map_file:
        dataset_manifest.append(json.loads(line))

    json_list = glob(os.path.join(data_path, '*.json'))
    classes_ids = {}
    for json_file in json_list:
        data_json = json.load(open(json_file))
        for img in data_json:
            if 'consolidatedAnnotation' not in img.keys():
                print('Wrong json files')
                raise Exception

            manifest = dataset_manifest[int(img['datasetObjectId'])]
            file_name = os.path.basename(
                manifest['source-ref']
            ) + '___objects.json'

            classes = img['consolidatedAnnotation']['content'][
                main_key + '-metadata']['class-map']
            for key, value in classes.items():
                if key not in classes_ids.keys():
                    classes_ids[key] = value

            annotations = img['consolidatedAnnotation']['content'][main_key][
                'annotations']
            sa_loader = []
            for annotation in annotations:
                points = {
                    'x1': annotation['left'],
                    'y1': annotation['top'],
                    'x2': annotation['left'] + annotation['width'],
                    'y2': annotation['top'] + annotation['height']
                }
                sa_obj = {
                    'type': 'bbox',
                    'points': points,
                    'className': classes[str(annotation['class_id'])],
                    'classId': int(annotation['class_id']),
                    'attributes': [],
                    'probability': 100,
                    'locked': False,
                    'visible': True,
                    'groupId': 0
                }
                sa_loader.append(sa_obj.copy())
            sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes(classes_ids)
    return sa_jsons, sa_classes, None
