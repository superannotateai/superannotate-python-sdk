import json
import numpy as np

from pathlib import Path

from ..sa_json_helper import _create_vector_instance
from .dataloop_helper import (
    _create_sa_classes, _update_classes_dict, _create_attributes_list
)


def dataloop_object_detection_to_sa_vector(input_dir):
    classes = {}
    sa_jsons = {}
    json_data = Path(input_dir).glob('*.json')
    sa_classes_labels = ['point', 'box', 'ellipse', 'segment', 'binary']
    for json_file in json_data:
        sa_loader = []
        dl_data = json.load(open(json_file))

        for ann in dl_data['annotations']:
            if ann['type'] in sa_classes_labels:
                classes = _update_classes_dict(
                    classes, ann['label'], ann['attributes']
                )

            attributes = _create_attributes_list(ann['attributes'])

            if ann['type'] == 'box':
                points = {
                    'x1': ann['coordinates'][0]['x'],
                    'y1': ann['coordinates'][0]['y'],
                    'x2': ann['coordinates'][1]['x'],
                    'y2': ann['coordinates'][1]['y']
                }
                sa_obj = _create_vector_instance(
                    'bbox', points, {}, attributes, ann['label']
                )
                sa_loader.append(sa_obj)
            elif ann['type'] == 'note':
                sa_comment = {
                    'type': 'comment',
                    'x': ann['coordinates']['box'][0]['x'],
                    'y': ann['coordinates']['box'][0]['y'],
                    'comments': []
                }
                for note in ann['coordinates']['note']['messages']:
                    sa_comment['comments'].append(
                        {
                            'text': note['body'],
                            'id': note['creator']
                        }
                    )
                sa_loader.append(sa_comment)
            elif ann['type'] == 'class':
                sa_tags = {'type': 'tag', 'name': ann['label']}
                sa_loader.append(sa_tags)

        file_name = dl_data['filename'][1:] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    classes = _create_sa_classes(classes)
    return sa_jsons, classes


def dataloop_instance_segmentation_to_sa_vector(input_dir):
    classes = {}
    sa_jsons = {}
    json_data = Path(input_dir).glob('*.json')
    sa_classes_labels = ['point', 'box', 'ellipse', 'segment', 'binary']
    for json_file in json_data:
        sa_loader = []
        dl_data = json.load(open(json_file))

        for ann in dl_data['annotations']:
            if ann['type'] in sa_classes_labels:
                classes = _update_classes_dict(
                    classes, ann['label'], ann['attributes']
                )

            attributes = _create_attributes_list(ann['attributes'])

            if ann['type'] == 'segment' and len(ann['coordinates']) == 1:
                points = []
                for sub_list in ann['coordinates']:
                    for sub_dict in sub_list:
                        points.append(sub_dict['x'])
                        points.append(sub_dict['y'])
                sa_obj = _create_vector_instance(
                    'polygon', points, {}, attributes, ann['label']
                )
                sa_loader.append(sa_obj)
            elif ann['type'] == 'note':
                sa_comment = {
                    'type': 'comment',
                    'x': ann['coordinates']['box'][0]['x'],
                    'y': ann['coordinates']['box'][0]['y'],
                    'comments': []
                }
                for note in ann['coordinates']['note']['messages']:
                    sa_comment['comments'].append(
                        {
                            'text': note['body'],
                            'id': note['creator']
                        }
                    )
                sa_loader.append(sa_comment)
            elif ann['type'] == 'class':
                sa_tags = {'type': 'tag', 'name': ann['label']}
                sa_loader.append(sa_tags)

        file_name = dl_data['filename'][1:] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    classes = _create_sa_classes(classes)
    return sa_jsons, classes


def dataloop_to_sa(input_dir):
    classes = {}
    sa_jsons = {}
    json_data = Path(input_dir).glob('*.json')
    sa_classes_labels = ['point', 'box', 'ellipse', 'segment', 'binary']
    for json_file in json_data:
        sa_loader = []
        dl_data = json.load(open(json_file))

        for ann in dl_data['annotations']:
            if ann['type'] in sa_classes_labels:
                classes = _update_classes_dict(
                    classes, ann['label'], ann['attributes']
                )

            attributes = _create_attributes_list(ann['attributes'])

            if ann['type'] == 'segment' and len(ann['coordinates']) == 1:
                points = []
                for sub_list in ann['coordinates']:
                    for sub_dict in sub_list:
                        points.append(sub_dict['x'])
                        points.append(sub_dict['y'])
                sa_obj = _create_vector_instance(
                    'polygon', points, {}, attributes, ann['label']
                )
                sa_loader.append(sa_obj)
            elif ann['type'] == 'box':
                points = {
                    'x1': ann['coordinates'][0]['x'],
                    'y1': ann['coordinates'][0]['y'],
                    'x2': ann['coordinates'][1]['x'],
                    'y2': ann['coordinates'][1]['y']
                }
                sa_obj = _create_vector_instance(
                    'bbox', points, {}, attributes, ann['label']
                )
                sa_loader.append(sa_obj)
            elif ann['type'] == 'ellipse':
                points = (
                    ann['coordinates']['center']['x'],
                    ann['coordinates']['center']['y'], ann['coordinates']['rx'],
                    ann['coordinates']['ry'], ann['coordinates']['angle']
                )
                sa_obj = _create_vector_instance(
                    'ellipse', points, {}, attributes, ann['label']
                )
            elif ann['type'] == 'point':
                points = (ann['coordinates']['x'], ann['coordinates']['y'])
                sa_obj = _create_vector_instance(
                    'point', points, {}, attributes, ann['label']
                )
            elif ann['type'] == 'note':
                sa_comment = {
                    'type': 'comment',
                    'x': ann['coordinates']['box'][0]['x'],
                    'y': ann['coordinates']['box'][0]['y'],
                    'comments': []
                }
                for note in ann['coordinates']['note']['messages']:
                    sa_comment['comments'].append(
                        {
                            'text': note['body'],
                            'id': note['creator']
                        }
                    )
                sa_loader.append(sa_comment)
            elif ann['type'] == 'class':
                sa_tags = {'type': 'tag', 'name': ann['label']}
                sa_loader.append(sa_tags)

        file_name = dl_data['filename'][1:] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    classes = _create_sa_classes(classes)
    return sa_jsons, classes
