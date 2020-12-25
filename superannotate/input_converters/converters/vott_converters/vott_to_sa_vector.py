'''
'''
import json

from ..sa_json_helper import _create_vector_instance

from ....common import write_to_json


def vott_to_sa(file_list, task, output_dir):
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

        write_to_json(output_dir / file_name, sa_loader)
    return set(classes)
