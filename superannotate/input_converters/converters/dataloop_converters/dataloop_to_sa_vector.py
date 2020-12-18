import json
import numpy as np

from pathlib import Path


def _create_classes(classes):
    sa_classes_loader = []
    for key, value in classes.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {'name': key, 'color': hexcolor, 'attribute_groups': []}
        attribute_groups = []
        for attr_group_key, attr_group in value['attribute_group'].items():
            attr_loader = {
                'name': attr_group_key,
                'is_multiselect': attr_group['is_multiselect'],
                'attributes': []
            }
            for attr in set(attr_group['attributes']):
                attr_loader['attributes'].append({'name': attr})
            if attr_loader:
                attribute_groups.append(attr_loader)

        sa_classes['attribute_groups'] = attribute_groups

        sa_classes_loader.append(sa_classes)
    return sa_classes_loader


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
                if ann['label'] not in classes.keys():
                    classes[ann['label']] = {'attribute_group': {}}
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'] = {}
                    classes[ann['label']]['attribute_group'][
                        'converted_attributes']['is_multiselect'] = 1
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'][
                               'attributes'] = ann['attributes']
                else:
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'][
                               'attributes'] += ann['attributes']

            attributes = []
            for attribute in ann['attributes']:
                attr = {'name': attribute, 'groupName': 'converted_attributes'}
                attributes.append(attr)

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
                    'attributes': attributes,
                    'probability': 100,
                    'locked': False,
                    'visible': True,
                    'groupId': 0
                }
                sa_loader.append(sa_bbox)
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

    classes = _create_classes(classes)
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
                if ann['label'] not in classes.keys():
                    classes[ann['label']] = {'attribute_group': {}}
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'] = {}
                    classes[ann['label']]['attribute_group'][
                        'converted_attributes']['is_multiselect'] = 1
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'][
                               'attributes'] = ann['attributes']
                else:
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'][
                               'attributes'] += ann['attributes']

            attributes = []
            for attribute in ann['attributes']:
                attr = {'name': attribute, 'groupName': 'converted_attributes'}
                attributes.append(attr)

            if ann['type'] == 'segment' and len(ann['coordinates']) == 1:
                sa_polygon = {
                    'type': 'polygon',
                    'points': [],
                    'className': ann['label'],
                    'attributes': attributes,
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

    classes = _create_classes(classes)
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
                if ann['label'] not in classes.keys():
                    classes[ann['label']] = {'attribute_group': {}}
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'] = {}
                    classes[ann['label']]['attribute_group'][
                        'converted_attributes']['is_multiselect'] = 1
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'][
                               'attributes'] = ann['attributes']
                else:
                    classes[ann['label']
                           ]['attribute_group']['converted_attributes'][
                               'attributes'] += ann['attributes']

            attributes = []
            for attribute in ann['attributes']:
                attr = {'name': attribute, 'groupName': 'converted_attributes'}
                attributes.append(attr)

            if ann['type'] == 'segment' and len(ann['coordinates']) == 1:
                sa_polygon = {
                    'type': 'polygon',
                    'points': [],
                    'className': ann['label'],
                    'attributes': attributes,
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
            elif ann['type'] == 'box':
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
                    'attributes': attributes,
                    'probability': 100,
                    'locked': False,
                    'visible': True,
                    'groupId': 0
                }
                sa_loader.append(sa_bbox)
            elif ann['type'] == 'ellipse':
                sa_ellipse = {
                    'type': 'ellipse',
                    'className': ann['label'],
                    'probability': 100,
                    'cx': ann['coordinates']['center']['x'],
                    'cy': ann['coordinates']['center']['y'],
                    'rx': ann['coordinates']['rx'],
                    'ry': ann['coordinates']['ry'],
                    'angle': ann['coordinates']['angle'],
                    'groupId': 0,
                    'pointLabels': {},
                    'attributes': attributes,
                    'locked': False,
                    'visible': True,
                    'attributes': []
                }
                sa_loader.append(sa_ellipse)
            elif ann['type'] == 'point':
                sa_point = {
                    'type': 'point',
                    'className': ann['label'],
                    'probability': 100,
                    'x': ann['coordinates']['x'],
                    'y': ann['coordinates']['y'],
                    'groupId': 0,
                    'pointLabels': {},
                    'attributes': attributes,
                    'locked': False,
                    'visible': True,
                    'attributes': []
                }
                sa_loader.append(sa_point)
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

    classes = _create_classes(classes)
    return sa_jsons, classes
