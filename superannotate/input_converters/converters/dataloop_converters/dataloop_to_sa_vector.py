import json
import os
import numpy as np


def _create_classes(classes):
    sa_classes = []
    for class_, id_ in classes.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_class = {
            "id": id_,
            "name": class_,
            "color": hexcolor,
            "attribute_groups": []
        }
        sa_classes.append(sa_class)
    return sa_classes


def dataloop_object_detection_to_sa_vector(input_dir):
    classes = {}
    id_ = 1
    sa_jsons = {}
    for json_file in os.listdir(input_dir):
        sa_loader = []
        dl_data = json.load(open(os.path.join(input_dir, json_file)))

        for ann in dl_data['annotations']:
            if ann['label'] not in classes.keys():
                classes[ann['label']] = id_
                id_ += 1

            if ann['type'] == 'box':
                sa_bbox = {
                    'type': 'bbox',
                    'points':
                        {
                            'x1': ann['coordinates'][0]['x'],
                            'y1': ann['coordinates'][0]['y'],
                            'x2': ann['coordinates'][1]['x'],
                            'y2': ann['coordinates'][1]['y']
                        },
                    'className': ann['label'],
                    'classId': classes[ann['label']],
                    'attributes': [],
                    'probability': 100,
                    'locked': False,
                    'visible': True,
                    'groupId': 0
                }
                sa_loader.append(sa_bbox)

        file_name = dl_data['filename'][1:] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    classes = _create_classes(classes)
    return classes, sa_jsons


def dataloop_instance_segmentation_to_sa_vector(input_dir):
    classes = {}
    id_ = 1
    sa_jsons = {}
    for json_file in os.listdir(input_dir):
        sa_loader = []
        dl_data = json.load(open(os.path.join(input_dir, json_file)))

        for ann in dl_data['annotations']:
            if ann['label'] not in classes.keys():
                classes[ann['label']] = id_
                id_ += 1

                if ann['type'] == 'segment' and len(ann['coordinates']) == 1:
                    sa_polygon = {
                        'type': 'polygon',
                        'points': [],
                        'className': ann['label'],
                        'classId': classes[ann['label']],
                        'attributes': [],
                        'probability': 100,
                        'locked': False,
                        'visible': True,
                        'groupId': 0,
                    }
                    for sub_list in ann['coordinates']:
                        for sub_dict in sub_list:
                            sa_polygon['points'].append(sub_dict['x'])
                            sa_polygon['points'].append(sub_dict['y'])

                    sa_loader.append(sa_polygon)

        file_name = dl_data['filename'][1:] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    classes = _create_classes(classes)
    return classes, sa_jsons
