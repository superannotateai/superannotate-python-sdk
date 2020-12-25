from .labelbox_helper import (
    _create_classes_json, _create_classes_id_map, _create_attributes_list
)
from ..sa_json_helper import _create_vector_instance


def labelbox_to_sa(json_data, task):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    if task == 'object_detection':
        instance_types = ['bbox']
    elif task == 'instance_segmentation':
        instance_types = ['polygon']
    elif task == 'vector_annotation':
        instance_types = ['bbox', 'polygon', 'line', 'point']

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

            lb_type = list(set(instance_types) & set(instance.keys()))
            if len(lb_type) != 1:
                continue

            if lb_type[0] == 'bbox':
                points = (
                    instance['bbox']['left'], instance['bbox']['top'],
                    instance['bbox']['left'] + instance['bbox']['width'],
                    instance['bbox']['top'] + instance['bbox']['height']
                )
                instance_type = 'bbox'
            elif lb_type[0] == 'polygon':
                points = []
                for point in instance['polygon']:
                    points.append(point['x'])
                    points.append(point['y'])
                instance_type = 'polygon'
            elif lb_type[0] == 'line':
                points = []
                for point in instance['line']:
                    points.append(point['x'])
                    points.append(point['y'])
                instance_type = 'polyline'
            elif lb_type[0] == 'point':
                points = (instance['point']['x'], instance['point']['y'])
                instance_type = 'point'

            sa_obj = _create_vector_instance(
                instance_type, points, {}, attributes, class_name
            )
            sa_loader.append(sa_obj)

        file_name = '%s___objects.json' % d['External ID']
        sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, None
