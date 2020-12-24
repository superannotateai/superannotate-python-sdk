import json

from .vgg_helper import _create_classes, _create_attribute_list
from ..sa_json_helper import _create_vector_instance


def vgg_object_detection_to_sa_vector(json_data):
    sa_jsons = {}
    all_jsons = []
    for path in json_data:
        all_jsons.append(json.load(open(path)))

    class_id_map = {}
    for images in all_jsons:
        for key, img in images.items():
            file_name = img['filename'] + '___objects.json'
            sa_loader = []
            instances = img['regions']
            for instance in instances:
                if 'type' not in instance['region_attributes'].keys():
                    raise KeyError(
                        "'VGG' JSON should contain 'type' key which will be category name. Please correct JSON file."
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
                if instance['shape_attributes']['name'] == 'rect':
                    points = {
                        'x1':
                            instance['shape_attributes']['x'],
                        'y1':
                            instance['shape_attributes']['y'],
                        'x2':
                            instance['shape_attributes']['x'] +
                            instance['shape_attributes']['width'],
                        'y2':
                            instance['shape_attributes']['y'] +
                            instance['shape_attributes']['height']
                    }
                    sa_obj = _create_vector_instance(
                        'bbox', points, {}, attributes, class_name
                    )
                    sa_loader.append(sa_obj)
            sa_jsons[file_name] = sa_loader

        sa_classes = _create_classes(class_id_map)
    return sa_jsons, sa_classes


def vgg_instance_segmentation_to_sa_vector(json_data):
    sa_jsons = {}
    all_jsons = []
    for path in json_data:
        all_jsons.append(json.load(open(path)))

    class_id_map = {}
    for images in all_jsons:
        for key, img in images.items():
            file_name = img['filename'] + '___objects.json'
            sa_loader = []
            instances = img['regions']
            for instance in instances:
                if instance['shape_attributes']['name'] != 'polygon':
                    continue

                if 'type' not in instance['region_attributes'].keys():
                    raise KeyError(
                        "'VGG' JSON should contain 'type' key which will be category name. Please correct JSON file."
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
                if instance['shape_attributes']['name'] == 'polygon':
                    points = []
                    for x, y in zip(
                        instance['shape_attributes']['all_points_x'],
                        instance['shape_attributes']['all_points_y']
                    ):
                        points.append(x)
                        points.append(y)
                    sa_obj = _create_vector_instance(
                        'polygon', points, {}, attributes, class_name
                    )
                    sa_loader.append(sa_obj)
            sa_jsons[file_name] = sa_loader

        sa_classes = _create_classes(class_id_map)
    return sa_jsons, sa_classes


def vgg_to_sa(json_data):
    sa_jsons = {}
    all_jsons = []
    for path in json_data:
        all_jsons.append(json.load(open(path)))

    class_id_map = {}
    for images in all_jsons:
        for key, img in images.items():
            file_name = img['filename'] + '___objects.json'
            sa_loader = []
            instances = img['regions']
            for instance in instances:
                if 'type' not in instance['region_attributes'].keys():
                    raise KeyError(
                        "'VGG' JSON should contain 'type' key which will be category name. Please correct JSON file."
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
                if instance['shape_attributes']['name'] == 'polygon' or instance[
                    'shape_attributes']['name'] == 'polyline':
                    points = []
                    for x, y in zip(
                        instance['shape_attributes']['all_points_x'],
                        instance['shape_attributes']['all_points_y']
                    ):
                        points.append(x)
                        points.append(y)
                    sa_obj = _create_vector_instance(
                        instance['shape_attributes']['name'], points, {},
                        attributes, class_name
                    )
                    sa_loader.append(sa_obj)
                elif instance['shape_attributes']['name'] == 'rect':
                    points = {
                        'x1':
                            instance['shape_attributes']['x'],
                        'y1':
                            instance['shape_attributes']['y'],
                        'x2':
                            instance['shape_attributes']['x'] +
                            instance['shape_attributes']['width'],
                        'y2':
                            instance['shape_attributes']['y'] +
                            instance['shape_attributes']['height']
                    }
                    sa_obj = _create_vector_instance(
                        'bbox', points, {}, attributes, class_name
                    )
                    sa_loader.append(sa_obj)
                elif instance['shape_attributes']['name'] == 'ellipse':
                    points = (
                        instance['shape_attributes']['cx'],
                        instance['shape_attributes']['cy'],
                        instance['shape_attributes']['rx'],
                        instance['shape_attributes']['ry'],
                        instance['shape_attributes']['theta']
                    )
                    sa_obj = _create_vector_instance(
                        'ellipse', points, {}, attributes, class_name
                    )
                    sa_loader.append(sa_obj)
                elif instance['shape_attributes']['name'] == 'circle':
                    points = (
                        instance['shape_attributes']['cx'],
                        instance['shape_attributes']['cy'],
                        instance['shape_attributes']['r'],
                        instance['shape_attributes']['r'], 0
                    )
                    sa_obj = _create_vector_instance(
                        'ellipse', points, {}, attributes, class_name
                    )
                    sa_loader.append(sa_obj)
                elif instance['shape_attributes']['name'] == 'point':
                    points = (
                        instance['shape_attributes']['cx'],
                        instance['shape_attributes']['cy']
                    )
                    sa_obj = _create_vector_instance(
                        'point', points, {}, attributes, class_name
                    )
                    sa_loader.append(sa_obj)
            sa_jsons[file_name] = sa_loader

        sa_classes = _create_classes(class_id_map)
    return sa_jsons, sa_classes