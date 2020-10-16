import json
import numpy as np
from ....common import rgb_to_hex


def _create_classes(class_id_map):
    sa_classes = []
    for key in class_id_map.keys():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        dd = {
            'id': class_id_map[key]['id'],
            'name': key,
            'color': hexcolor,
            'attribute_groups': []
        }
        for attributes, value in class_id_map[key]['attribute_groups'].items():
            attr_group = {
                'id': value['id'],
                'class_id': class_id_map[key]['id'],
                'name': attributes,
                'is_multiselect': value['is_multiselect'],
                'attributes': []
            }
            for attribute, attr_value in value['attributes'].items():
                attr = {
                    'id': attr_value,
                    'group_id': value['id'],
                    'name': attribute,
                    'groupName': attributes
                }
                attr_group['attributes'].append(attr.copy())
            dd['attribute_groups'].append(attr_group.copy())
        sa_classes.append(dd)
    return sa_classes


def vgg_object_detection_to_sa_vector(json_data, id_generator):
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
                    class_id_map[class_name] = {
                        'id': next(id_generator),
                        'attribute_groups': {}
                    }

                attr_keys = instance['region_attributes'].keys()
                attributes = []
                for attr in attr_keys:
                    if attr == 'type':
                        continue

                    if attr in class_id_map[class_name]['attribute_groups'
                                                       ].keys():
                        group_id = class_id_map[class_name]['attribute_groups'][
                            attr]['id']
                        group_name = attr
                        if isinstance(
                            instance['region_attributes'][attr], dict
                        ):
                            keys = instance['region_attributes'][attr].keys()
                        else:
                            keys = [instance['region_attributes'][attr]]

                        for key in keys:
                            if key not in class_id_map[class_name][
                                'attribute_groups'][attr]['attributes'].keys():
                                class_id_map[class_name]['attribute_groups'][
                                    attr]['attributes'][key] = next(
                                        id_generator
                                    )
                            dd = {
                                'id':
                                    class_id_map[class_name]['attribute_groups']
                                    [attr]['attributes'][key],
                                'name':
                                    key,
                                'groupId':
                                    group_id,
                                'groupName':
                                    group_name
                            }
                            attributes.append(dd.copy())

                    else:
                        multi = 0
                        if isinstance(
                            instance['region_attributes'][attr], dict
                        ):
                            multi = 1

                        class_id_map[class_name]['attribute_groups'][attr] = {
                            'id': next(id_generator),
                            'is_multiselect': multi,
                            'attributes': {}
                        }

                sa_obj = {
                    'className': class_name,
                    'classId': class_id_map[class_name]['id'],
                    'attributes': attributes,
                    'pointLabels': {},
                    'probability': 100,
                    'locked': False,
                    'visible': True,
                    'groupId': 0
                }
                if instance['shape_attributes']['name'] == 'polygon':
                    points = {
                        'x1': min(instance['shape_attributes']['all_points_x']),
                        'y1': min(instance['shape_attributes']['all_points_y']),
                        'x2': max(instance['shape_attributes']['all_points_x']),
                        'y2': max(instance['shape_attributes']['all_points_y'])
                    }
                    sa_obj['points'] = points
                    sa_obj['type'] = 'bbox'
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
                    sa_obj['points'] = points
                    sa_obj['type'] = 'bbox'
                elif instance['shape_attributes']['name'] == 'ellipse':
                    if instance['shape_attributes']['rx'] > instance[
                        'shape_attributes']['ry']:
                        rx = instance['shape_attributes']['rx'] * np.cos(
                            instance['shape_attributes']['theta']
                        )
                        ry = max(
                            instance['shape_attributes']['rx'] *
                            np.sin(instance['shape_attributes']['theta']),
                            instance['shape_attributes']['ry']
                        )
                    else:
                        ry = instance['shape_attributes']['ry'] * np.sin(
                            instance['shape_attributes']['theta']
                        )
                        ry = max(
                            instance['shape_attributes']['ry'] *
                            np.cos(instance['shape_attributes']['theta']),
                            instance['shape_attributes']['rx']
                        )
                    points = {
                        'x1': instance['shape_attributes']['cx'] - rx,
                        'y1': instance['shape_attributes']['cy'] - ry,
                        'x2': instance['shape_attributes']['cx'] + rx,
                        'y2': instance['shape_attributes']['cy'] + ry
                    }
                    sa_obj['type'] = 'bbox'
                elif instance['shape_attributes']['name'] == 'circle':
                    points = {
                        'x1':
                            instance['shape_attributes']['cx'] -
                            instance['shape_attributes']['r'],
                        'y1':
                            instance['shape_attributes']['cy'] -
                            instance['shape_attributes']['r'],
                        'x2':
                            instance['shape_attributes']['cx'] +
                            instance['shape_attributes']['r'],
                        'y2':
                            instance['shape_attributes']['cy'] +
                            instance['shape_attributes']['r']
                    }
                    sa_obj['type'] = 'bbox'
                sa_obj['points'] = points

                sa_loader.append(sa_obj)
            sa_jsons[file_name] = sa_loader

        sa_classes = _create_classes(class_id_map)
    return sa_jsons, sa_classes


def vgg_instance_segmentation_to_sa_vector(json_data, id_generator):
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
                    class_id_map[class_name] = {
                        'id': next(id_generator),
                        'attribute_groups': {}
                    }

                attr_keys = instance['region_attributes'].keys()
                attributes = []
                for attr in attr_keys:
                    if attr == 'type':
                        continue

                    if attr in class_id_map[class_name]['attribute_groups'
                                                       ].keys():
                        group_id = class_id_map[class_name]['attribute_groups'][
                            attr]['id']
                        group_name = attr
                        if isinstance(
                            instance['region_attributes'][attr], dict
                        ):
                            keys = instance['region_attributes'][attr].keys()
                        else:
                            keys = [instance['region_attributes'][attr]]

                        for key in keys:
                            if key not in class_id_map[class_name][
                                'attribute_groups'][attr]['attributes'].keys():
                                class_id_map[class_name]['attribute_groups'][
                                    attr]['attributes'][key] = next(
                                        id_generator
                                    )
                            dd = {
                                'id':
                                    class_id_map[class_name]['attribute_groups']
                                    [attr]['attributes'][key],
                                'name':
                                    key,
                                'groupId':
                                    group_id,
                                'groupName':
                                    group_name
                            }
                            attributes.append(dd.copy())

                    else:
                        multi = 0
                        if isinstance(
                            instance['region_attributes'][attr], dict
                        ):
                            multi = 1

                        class_id_map[class_name]['attribute_groups'][attr] = {
                            'id': next(id_generator),
                            'is_multiselect': multi,
                            'attributes': {}
                        }

                sa_obj = {
                    'className': class_name,
                    'classId': class_id_map[class_name]['id'],
                    'attributes': attributes,
                    'pointLabels': {},
                    'probability': 100,
                    'locked': False,
                    'visible': True,
                    'groupId': 0
                }
                points = []
                for x, y in zip(
                    instance['shape_attributes']['all_points_x'],
                    instance['shape_attributes']['all_points_y']
                ):
                    points.append(x)
                    points.append(y)
                sa_obj['points'] = points
                sa_obj['type'] = instance['shape_attributes']['name']

                sa_loader.append(sa_obj)
            sa_jsons[file_name] = sa_loader

        sa_classes = _create_classes(class_id_map)
    return sa_jsons, sa_classes


def vgg_to_sa(json_data, id_generator):
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
                    class_id_map[class_name] = {
                        'id': next(id_generator),
                        'attribute_groups': {}
                    }

                attr_keys = instance['region_attributes'].keys()
                attributes = []
                for attr in attr_keys:
                    if attr == 'type':
                        continue

                    if attr in class_id_map[class_name]['attribute_groups'
                                                       ].keys():
                        group_id = class_id_map[class_name]['attribute_groups'][
                            attr]['id']
                        group_name = attr
                        if isinstance(
                            instance['region_attributes'][attr], dict
                        ):
                            keys = instance['region_attributes'][attr].keys()
                        else:
                            keys = [instance['region_attributes'][attr]]

                        for key in keys:
                            if key not in class_id_map[class_name][
                                'attribute_groups'][attr]['attributes'].keys():
                                class_id_map[class_name]['attribute_groups'][
                                    attr]['attributes'][key] = next(
                                        id_generator
                                    )
                            dd = {
                                'id':
                                    class_id_map[class_name]['attribute_groups']
                                    [attr]['attributes'][key],
                                'name':
                                    key,
                                'groupId':
                                    group_id,
                                'groupName':
                                    group_name
                            }
                            attributes.append(dd.copy())

                    else:
                        multi = 0
                        if isinstance(
                            instance['region_attributes'][attr], dict
                        ):
                            multi = 1

                        class_id_map[class_name]['attribute_groups'][attr] = {
                            'id': next(id_generator),
                            'is_multiselect': multi,
                            'attributes': {}
                        }

                sa_obj = {
                    'className': class_name,
                    'classId': class_id_map[class_name]['id'],
                    'attributes': attributes,
                    'pointLabels': {},
                    'probability': 100,
                    'locked': False,
                    'visible': True,
                    'groupId': 0
                }
                if instance['shape_attributes']['name'] == 'polygon' or instance[
                    'shape_attributes']['name'] == 'polyline':
                    points = []
                    for x, y in zip(
                        instance['shape_attributes']['all_points_x'],
                        instance['shape_attributes']['all_points_y']
                    ):
                        points.append(x)
                        points.append(y)
                    sa_obj['points'] = points
                    sa_obj['type'] = instance['shape_attributes']['name']
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
                    sa_obj['points'] = points
                    sa_obj['type'] = 'bbox'
                elif instance['shape_attributes']['name'] == 'ellipse':
                    sa_obj['type'] = 'ellipse'
                    sa_obj['cx'] = instance['shape_attributes']['cx']
                    sa_obj['cy'] = instance['shape_attributes']['cy']
                    sa_obj['rx'] = instance['shape_attributes']['rx']
                    sa_obj['ry'] = instance['shape_attributes']['ry']
                    sa_obj['angle'] = instance['shape_attributes']['theta']
                elif instance['shape_attributes']['name'] == 'circle':
                    sa_obj['type'] = 'ellipse'
                    sa_obj['cx'] = instance['shape_attributes']['cx']
                    sa_obj['cy'] = instance['shape_attributes']['cy']
                    sa_obj['rx'] = instance['shape_attributes']['r']
                    sa_obj['ry'] = instance['shape_attributes']['r']
                    sa_obj['angle'] = 0
                elif instance['shape_attributes']['name'] == 'point':
                    sa_obj['type'] = 'point'
                    sa_obj['x'] = instance['shape_attributes']['cx']
                    sa_obj['y'] = instance['shape_attributes']['cy']

                sa_loader.append(sa_obj)
            sa_jsons[file_name] = sa_loader

        sa_classes = _create_classes(class_id_map)
    return sa_jsons, sa_classes