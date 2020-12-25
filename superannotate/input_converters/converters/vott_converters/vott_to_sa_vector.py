import json
import numpy as np

from ..sa_json_helper import _create_vector_instance


def _create_classes(classes_map):
    classes_loader = []
    for key in classes_map:
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {'name': key, 'color': hexcolor, 'attribute_groups': []}
        classes_loader.append(sa_classes)
    return classes_loader


def vott_to_sa(file_list, task):
    sa_jsons = {}
    classes = []
    if task == 'object_detection':
        instance_types = ['RECTANGLE']
    elif task == 'instance_segmentation':
        instance_types = ['POLYGON']
    elif task == 'vector_annotation':
        instance_types = ['RECTANGLE', 'POLYGON']

    for json_file in file_list:
        json_data = json.load(open(json_file))
        file_name = '%s___objects.json' % json_data['asset']['name']

        instances = json_data['regions']
        sa_loader = []
        for instance in instances:
            for tag in instance['tags']:
                classes.append(tag)

            if instance['type'] in instance_types:
                if instance['type'] == 'RECTANGLE':
                    instance_type = 'bbox'
                    points = (
                        instance['boundingBox']['left'],
                        instance['boundingBox']['top'],
                        instance['boundingBox']['left'] +
                        instance['boundingBox']['width'],
                        instance['boundingBox']['top'] +
                        instance['boundingBox']['height']
                    )
                elif instance['type'] == 'POLYGON':
                    instance_type = 'polygon'
                    points = []
                    for point in instance['points']:
                        points.append(point['x'])
                        points.append(point['y'])

                sa_obj = _create_vector_instance(
                    instance_type, points, {}, [], instance['tags'][0]
                )
                sa_loader.append(sa_obj.copy())

        sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes(set(classes))
    return sa_jsons, sa_classes
