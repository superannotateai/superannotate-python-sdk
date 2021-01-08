'''
'''
import json

from .vgg_helper import _create_attribute_list
from ..sa_json_helper import (_create_vector_instance, _create_sa_json)

from ....common import write_to_json


def vgg_to_sa(json_data, task, output_dir):
    all_jsons = []
    for path in json_data:
        all_jsons.append(json.load(open(path)))

    if task == 'object_detection':
        instance_types = ['rect']
    elif task == 'instance_segmentation':
        instance_types = ['polygon']
    elif task == 'vector_annotation':
        instance_types = [
            'rect', 'polygon', 'polyline', 'point', 'ellipse', 'circle'
        ]

    class_id_map = {}
    for images in all_jsons:
        for _, img in images.items():
            file_name = '%s___objects.json' % img['filename']
            sa_metadata = {
                'name': img['filename'],
            }
            sa_instances = []
            instances = img['regions']
            for instance in instances:
                if 'type' not in instance['region_attributes'].keys():
                    raise KeyError(
                        "'VGG' JSON should contain 'type' key which will \
                        be category name. Please correct JSON file."
                    )
                if not isinstance(instance['region_attributes']['type'], str):
                    raise ValueError(
                        "Wrong attribute was choosen for 'type' attribute."
                    )

                class_name = instance['region_attributes']['type']
                if class_name not in class_id_map.keys():
                    class_id_map[class_name] = {'attribute_groups': {}}

                attributes = _create_attribute_list(
                    instance['region_attributes'], class_name, class_id_map
                )

                if instance['shape_attributes']['name'] in instance_types:
                    if instance['shape_attributes'][
                        'name'] == 'polygon' or instance['shape_attributes'][
                            'name'] == 'polyline':
                        points = []
                        for x, y in zip(
                            instance['shape_attributes']['all_points_x'],
                            instance['shape_attributes']['all_points_y']
                        ):
                            points.append(x)
                            points.append(y)
                        instance_type = instance['shape_attributes']['name']
                    elif instance['shape_attributes']['name'] == 'rect':
                        points = (
                            instance['shape_attributes']['x'],
                            instance['shape_attributes']['y'],
                            instance['shape_attributes']['x'] +
                            instance['shape_attributes']['width'],
                            instance['shape_attributes']['y'] +
                            instance['shape_attributes']['height']
                        )
                        instance_type = 'bbox'
                    elif instance['shape_attributes']['name'] == 'ellipse':
                        points = (
                            instance['shape_attributes']['cx'],
                            instance['shape_attributes']['cy'],
                            instance['shape_attributes']['rx'],
                            instance['shape_attributes']['ry'],
                            instance['shape_attributes']['theta']
                        )
                        instance_type = 'ellipse'
                    elif instance['shape_attributes']['name'] == 'circle':
                        points = (
                            instance['shape_attributes']['cx'],
                            instance['shape_attributes']['cy'],
                            instance['shape_attributes']['r'],
                            instance['shape_attributes']['r'], 0
                        )
                        instance_type = 'ellipse'
                    elif instance['shape_attributes']['name'] == 'point':
                        points = (
                            instance['shape_attributes']['cx'],
                            instance['shape_attributes']['cy']
                        )
                        instance_type = 'point'
                    sa_obj = _create_vector_instance(
                        instance_type, points, {}, attributes, class_name
                    )
                    sa_instances.append(sa_obj)
            sa_json = _create_sa_json(sa_instances, sa_metadata)
            write_to_json(output_dir / file_name, sa_json)
    return class_id_map
