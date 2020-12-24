import numpy as np
import os
import json
import zlib
import base64
import cv2

from .supervisely_helper import _base64_to_polygon, _create_attribute_list

from ..sa_json_helper import _create_vector_instance


def supervisely_to_sa(json_files, class_id_map):
    sa_jsons = {}
    for json_file in json_files:
        file_name = os.path.splitext(os.path.basename(json_file)
                                    )[0] + '___objects.json'

        json_data = json.load(open(json_file))
        sa_loader = []

        for obj in json_data['objects']:
            if 'classTitle' in obj and obj['classTitle'] in class_id_map.keys():
                attributes = []
                if 'tags' in obj.keys():
                    attributes = _create_attribute_list(
                        obj['tags'], obj['classTitle'], class_id_map
                    )
                    if obj['geometryType'] == 'point':
                        points = (
                            obj['points']['exterior'][0][0],
                            obj['points']['exterior'][0][1]
                        )
                        instance_type = 'point'
                    elif obj['geometryType'] == 'line':
                        instance_type = 'polyline'
                        points = [
                            item for el in obj['points']['exterior']
                            for item in el
                        ]
                    elif obj['geometryType'] == 'rectangle':
                        instance_type = 'bbox'
                        points = {
                            'x1': obj['points']['exterior'][0][0],
                            'y1': obj['points']['exterior'][0][1],
                            'x2': obj['points']['exterior'][1][0],
                            'y2': obj['points']['exterior'][1][1]
                        }
                    elif obj['geometryType'] == 'polygon':
                        instance_type = 'polygon'
                        points = [
                            item for el in obj['points']['exterior']
                            for item in el
                        ]
                    elif obj['geometryType'] == 'cuboid':
                        instance_type = 'cuboid'
                        points = {
                            'f1':
                                {
                                    'x': obj['points'][0][0],
                                    'y': obj['points'][0][1]
                                },
                            'f2':
                                {
                                    'x': obj['points'][2][0],
                                    'y': obj['points'][2][1],
                                },
                            'r1':
                                {
                                    'x': obj['points'][4][0],
                                    'y': obj['points'][4][1]
                                },
                            'r2':
                                {
                                    'x': obj['points'][5][0],
                                    'y': obj['points'][6][1],
                                }
                        }
                    elif obj['geometryType'] == 'bitmap':
                        for ppoints in _base64_to_polygon(
                            obj['bitmap']['data']
                        ):
                            points = [
                                x + obj['bitmap']['origin'][0] if i %
                                2 == 0 else x + obj['bitmap']['origin'][1]
                                for i, x in enumerate(ppoints)
                            ]
                        instance_type = 'polygon'

                    sa_obj = _create_vector_instance(
                        instance_type, points, {}, attributes, obj['classTitle']
                    )
                    sa_loader.append(sa_obj)
        sa_jsons[file_name] = sa_loader
    return sa_jsons


def supervisely_instance_segmentation_to_sa_vector(json_files, class_id_map):
    sa_jsons = {}
    for json_file in json_files:
        file_name = os.path.splitext(os.path.basename(json_file)
                                    )[0] + '___objects.json'

        json_data = json.load(open(json_file))
        sa_loader = []

        for obj in json_data['objects']:
            if 'classTitle' in obj and obj['classTitle'] in class_id_map.keys():
                attributes = []
                if 'tags' in obj.keys():
                    attributes = _create_attribute_list(
                        obj['tags'], obj['classTitle'], class_id_map
                    )
                    if obj['geometryType'] == 'polygon':
                        instance_type = 'polygon'
                        points = [
                            item for el in obj['points']['exterior']
                            for item in el
                        ]
                        sa_obj = _create_vector_instance(
                            instance_type, points, {}, attributes,
                            obj['classTitle']
                        )

        sa_jsons[file_name] = sa_loader
    return sa_jsons


def supervisely_object_detection_to_sa_vector(json_files, class_id_map):
    sa_jsons = {}
    for json_file in json_files:
        file_name = os.path.splitext(os.path.basename(json_file)
                                    )[0] + '___objects.json'

        json_data = json.load(open(json_file))
        sa_loader = []

        for obj in json_data['objects']:
            if 'classTitle' in obj and obj['classTitle'] in class_id_map.keys():
                attributes = []
                if 'tags' in obj.keys():
                    attributes = _create_attribute_list(
                        obj['tags'], obj['classTitle'], class_id_map
                    )

                    if obj['geometryType'] == 'rectangle':
                        instance_type = 'bbox'
                        points = {
                            'x1': obj['points']['exterior'][0][0],
                            'y1': obj['points']['exterior'][0][1],
                            'x2': obj['points']['exterior'][1][0],
                            'y2': obj['points']['exterior'][1][1]
                        }
                        sa_obj = _create_vector_instance(
                            instance_type, points, {}, attributes,
                            obj['classTitle']
                        )
                        sa_loader.append(sa_obj)
        sa_jsons[file_name] = sa_loader
    return sa_jsons


def supervisely_keypoint_detection_to_sa_vector(
    json_files, class_id_map, meta_json
):
    classes_skeleton = {}
    for class_ in meta_json['classes']:
        if class_['shape'] != 'graph':
            continue

        classes_skeleton[class_['title']] = {'edges': [], 'nodes': {}}
        nodes = class_['geometry_config']['nodes']
        for node, value in nodes.items():
            classes_skeleton[class_['title']]['nodes'][node] = value['label']

        edges = class_['geometry_config']['edges']
        for edge in edges:
            classes_skeleton[class_['title']]['edges'].append(
                (edge['src'], edge['dst'])
            )

    sa_jsons = {}
    for json_file in json_files:
        file_name = os.path.splitext(os.path.basename(json_file)
                                    )[0] + '___objects.json'

        json_data = json.load(open(json_file))
        sa_loader = []

        for obj in json_data['objects']:
            if 'classTitle' in obj and obj['classTitle'] in class_id_map.keys():
                attributes = []
                if 'tags' in obj.keys():
                    attributes = _create_attribute_list(
                        obj['tags'], obj['classTitle'], class_id_map
                    )

                    sa_obj = {
                        'type': '',
                        'points': [],
                        'className': obj['classTitle'],
                        'pointLabels': {},
                        'attributes': attributes,
                        'probability': 100,
                        'locked': False,
                        'visible': True,
                        'connections': []
                    }

                    if obj['geometryType'] == 'graph':
                        sa_obj['type'] = 'template'
                        good_nodes = []
                        nodes = obj['nodes']
                        index = 1
                        for node, value in nodes.items():
                            good_nodes.append(node)
                            sa_obj['points'].append(
                                {
                                    'id': index,
                                    'x': value['loc'][0],
                                    'y': value['loc'][1]
                                }
                            )
                            sa_obj['pointLabels'][index - 1] = classes_skeleton[
                                obj['classTitle']]['nodes'][node]
                            index += 1

                        index = 1
                        for edge in classes_skeleton[obj['classTitle']
                                                    ]['edges']:
                            if edge[0] not in good_nodes or edge[
                                1] not in good_nodes:
                                continue

                            sa_obj['connections'].append(
                                {
                                    'id': index,
                                    'from': good_nodes.index(edge[0]) + 1,
                                    'to': good_nodes.index(edge[1]) + 1,
                                }
                            )
                            index += 1

                    sa_loader.append(sa_obj)
        sa_jsons[file_name] = sa_loader
    return sa_jsons
