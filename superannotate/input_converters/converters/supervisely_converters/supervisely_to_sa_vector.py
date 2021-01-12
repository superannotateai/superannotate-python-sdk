from pathlib import Path
import json

from .supervisely_helper import _base64_to_polygon, _create_attribute_list

from ..sa_json_helper import _create_vector_instance, _create_sa_json

from ....common import write_to_json


def supervisely_to_sa(json_files, class_id_map, task, output_dir):
    if task == 'object_detection':
        instance_types = ['rectangle']
    elif task == 'instance_segmentation':
        instance_types = ['bitmap', 'polygon']
    elif task == 'vector_annotation':
        instance_types = [
            'point', 'rectangle', 'line', 'polygon', 'cuboid', 'bitmap'
        ]

    for json_file in json_files:
        json_data = json.load(open(json_file))
        file_name = '%s___objects.json' % Path(json_file).stem
        sa_metadata = {
            'name': Path(json_file).stem,
            'width': json_data['size']['width'],
            'height': json_data['size']['height']
        }

        sa_instances = []
        for obj in json_data['objects']:
            if 'classTitle' in obj and obj['classTitle'] in class_id_map.keys():
                attributes = []
                if 'tags' in obj.keys():
                    attributes = _create_attribute_list(
                        obj['tags'], obj['classTitle'], class_id_map
                    )

                if obj['geometryType'] in instance_types:
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
                        points = (
                            obj['points']['exterior'][0][0],
                            obj['points']['exterior'][0][1],
                            obj['points']['exterior'][1][0],
                            obj['points']['exterior'][1][1]
                        )
                    elif obj['geometryType'] == 'polygon':
                        instance_type = 'polygon'
                        points = [
                            item for el in obj['points']['exterior']
                            for item in el
                        ]
                    elif obj['geometryType'] == 'cuboid':
                        instance_type = 'cuboid'
                        points = (
                            obj['points'][0][0], obj['points'][0][1],
                            obj['points'][2][0], obj['points'][2][1],
                            obj['points'][4][0], obj['points'][4][1],
                            obj['points'][5][0], obj['points'][6][1]
                        )
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
                    sa_instances.append(sa_obj)
        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)


def supervisely_keypoint_detection_to_sa_vector(
    json_files, class_id_map, meta_json, output_dir
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

    for json_file in json_files:
        file_name = '%s___objects.json' % (Path(json_file).stem)
        sa_metadata = {'name': Path(json_file).stem}
        json_data = json.load(open(json_file))
        sa_instances = []

        for obj in json_data['objects']:
            if 'classTitle' in obj and obj['classTitle'] in class_id_map.keys():
                attributes = []
                if 'tags' in obj.keys():
                    attributes = _create_attribute_list(
                        obj['tags'], obj['classTitle'], class_id_map
                    )

                    if obj['geometryType'] == 'graph':
                        good_nodes = []
                        nodes = obj['nodes']
                        index = 1
                        points = []
                        pointLabels = {}
                        for node, value in nodes.items():
                            good_nodes.append(node)
                            points.append(
                                {
                                    'id': index,
                                    'x': value['loc'][0],
                                    'y': value['loc'][1]
                                }
                            )
                            pointLabels[index - 1] = classes_skeleton[
                                obj['classTitle']]['nodes'][node]
                            index += 1

                        index = 1
                        connections = []
                        for edge in classes_skeleton[obj['classTitle']
                                                    ]['edges']:
                            if edge[0] not in good_nodes or edge[
                                1] not in good_nodes:
                                continue

                            connections.append(
                                {
                                    'id': index,
                                    'from': good_nodes.index(edge[0]) + 1,
                                    'to': good_nodes.index(edge[1]) + 1,
                                }
                            )
                            index += 1
                        sa_obj = _create_vector_instance(
                            'template', points, pointLabels, attributes,
                            obj['classTitle'], connections
                        )
                        sa_instances.append(sa_obj)
        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)
