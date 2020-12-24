"""
"""
from .labelbox_helper import (
    _create_classes_json, _create_classes_id_map, _create_attributes_list
)
from ..sa_json_helper import _create_vector_instance


def labelbox_object_detection_to_sa_vector(json_data):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    for d in json_data:
        if 'objects' not in d['Label'].keys():
            file_name = d['External ID'] + '___objects.json'
            sa_jsons[file_name] = []
            continue

        instances = d["Label"]["objects"]
        sa_loader = []
        for instance in instances:
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                attributes = _create_attributes_list(
                    instance['classifications']
                )

            if 'bbox' in instance.keys():
                points = {
                    'x1': instance['bbox']['left'],
                    'x2': instance['bbox']['left'] + instance['bbox']['width'],
                    'y1': instance['bbox']['top'],
                    'y2': instance['bbox']['top'] + instance['bbox']['height']
                }
                sa_obj = _create_vector_instance(
                    'bbox', points, {}, attributes, class_name
                )
                sa_loader.append(sa_obj)

        file_name = d['External ID'] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, None


def labelbox_instance_segmentation_to_sa_vector(json_data):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    for d in json_data:
        if 'objects' not in d['Label'].keys():
            file_name = d['External ID'] + '___objects.json'
            sa_jsons[file_name] = []
            continue

        instances = d["Label"]["objects"]
        sa_loader = []
        for instance in instances:
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                attributes = _create_attributes_list(
                    instance['classifications']
                )
            if 'polygon' in instance.keys():
                points = []
                for point in instance['polygon']:
                    points.append(point['x'])
                    points.append(point['y'])
                sa_obj = _create_vector_instance(
                    'polygon', points, {}, attributes, class_name
                )

        file_name = d['External ID'] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, None


def labelbox_to_sa(json_data):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    for d in json_data:
        if 'objects' not in d['Label'].keys():
            file_name = d['External ID'] + '___objects.json'
            sa_jsons[file_name] = []
            continue

        instances = d["Label"]["objects"]
        sa_loader = []
        for instance in instances:
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                attributes = _create_attributes_list(
                    instance['classifications']
                )
            if 'bbox' in instance.keys():
                points = {
                    'x1': instance['bbox']['left'],
                    'x2': instance['bbox']['left'] + instance['bbox']['width'],
                    'y1': instance['bbox']['top'],
                    'y2': instance['bbox']['top'] + instance['bbox']['height']
                }
                sa_obj = _create_vector_instance(
                    'bbox', points, {}, attributes, class_name
                )
                sa_loader.append(sa_obj)
            elif 'polygon' in instance.keys():
                points = []
                for point in instance['polygon']:
                    points.append(point['x'])
                    points.append(point['y'])
                sa_obj = _create_vector_instance(
                    'polygon', points, {}, attributes, class_name
                )
                sa_loader.append(sa_obj)
            elif 'line' in instance.keys():
                points = []
                for point in instance['line']:
                    points.append(point['x'])
                    points.append(point['y'])
                sa_obj = _create_vector_instance(
                    'polyline', points, {}, attributes, class_name
                )
                sa_loader.append(sa_obj)
            elif 'point' in instance.keys():
                points = (instance['point']['x'], instance['point']['y'])
                sa_obj = _create_vector_instance(
                    'point', points, {}, attributes, class_name
                )
                sa_loader.append(sa_obj)

        file_name = d['External ID'] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, None