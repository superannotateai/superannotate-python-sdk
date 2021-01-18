from .labelbox_helper import (_create_classes_id_map, _create_attributes_list)
from ..sa_json_helper import (_create_vector_instance, _create_sa_json)

from ....common import write_to_json


def labelbox_to_sa(json_data, output_dir, task):
    classes = _create_classes_id_map(json_data)
    if task == 'object_detection':
        instance_types = ['bbox']
    elif task == 'instance_segmentation':
        instance_types = ['polygon']
    elif task == 'vector_annotation':
        instance_types = ['bbox', 'polygon', 'line', 'point']

    for data in json_data:
        if 'objects' not in data['Label'].keys():
            file_name = data['External ID'] + '___objects.json'
            write_to_json(output_dir / file_name, [])
            continue

        instances = data["Label"]["objects"]
        sa_instances = []

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
            sa_instances.append(sa_obj)

        file_name = '%s___objects.json' % data['External ID']
        sa_metadata = {'name': data['External ID']}
        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)
    return classes
