import requests
import logging
from pathlib import Path
import cv2
import numpy as np

from ....common import hex_to_rgb, blue_color_generator

logger = logging.getLogger("superannotate-python-sdk")


def image_downloader(url, file_name):
    logger.info("Downloading mask for {}".format(file_name))
    r = requests.get(url, stream=True)
    with open(file_name, 'wb') as f:
        f.write(r.content)


def _create_classes_json(classes):
    sa_classes_loader = []
    for key, value in classes.items():
        sa_classes = {
            'name': key,
            'color': value['color'],
            'attribute_groups': []
        }
        attribute_groups = []
        for attr_group_key, attr_group in value['attribute_groups'].items():
            attr_loader = {
                'name': attr_group_key,
                'is_multiselect': attr_group['is_multiselect'],
                'attributes': []
            }
            for attr in attr_group['attributes']:
                attr_loader['attributes'].append({'name': attr})
            if attr_loader:
                attribute_groups.append(attr_loader)
        sa_classes['attribute_groups'] = attribute_groups

        sa_classes_loader.append(sa_classes)

    return sa_classes_loader


def _create_classes_id_map(json_data):
    classes = {}
    for d in json_data:
        if 'objects' not in d['Label'].keys():
            continue

        instances = d["Label"]["objects"]
        for instance in instances:
            class_name = instance["value"]
            if class_name not in classes.keys():
                color = instance["color"]
                classes[class_name] = {"color": color, 'attribute_groups': {}}

            if 'classifications' in instance.keys():
                classifications = instance['classifications']
                for classification in classifications:
                    if classification['value'] not in classes[class_name][
                        'attribute_groups']:
                        if 'answer' in classification.keys():
                            if isinstance(classification['answer'], str):
                                continue

                            classes[class_name]['attribute_groups'][
                                classification['value']] = {
                                    'is_multiselect': 0,
                                    'attributes': []
                                }
                            classes[class_name]['attribute_groups'][
                                classification['value']]['attributes'].append(
                                    classification['answer']['value']
                                )

                        elif 'answers' in classification.keys():
                            classes[class_name]['attribute_groups'][
                                classification['value']] = {
                                    'is_multiselect': 1,
                                    'attributes': []
                                }
                            for attr in classification['answers']:
                                classes[class_name]['attribute_groups'][
                                    classification['value']
                                ]['attributes'].append(attr['value'])

                    else:
                        if 'answer' in classification.keys():
                            classes[class_name]['attribute_groups'][
                                classification['value']]['attributes'].append(
                                    classification['answer']['value']
                                )
                        elif 'answers' in classification.keys():
                            for attr in classification['answers']:
                                classes[class_name]['attribute_groups'][
                                    classification['value']
                                ]['attributes'].append(attr['value'])
    return classes


def labelbox_instance_segmentation_to_sa_pixel(json_data):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    sa_masks = {}
    for d in json_data:
        file_name = d['External ID'] + '___pixel.json'
        mask_name = d['External ID'] + '___save.png'
        if 'objects' not in d['Label'].keys():
            sa_jsons[file_name] = []
            continue

        instances = d["Label"]["objects"]
        sa_loader = []
        blue_colors = blue_color_generator(len(instances))

        for i, instance in enumerate(instances):
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                classifications = instance['classifications']
                for classification in classifications:
                    group_name = classification['value']
                    if 'answer' in classification.keys(
                    ) and isinstance(classification['answer'], dict):
                        attribute_name = classification['answer']['value']
                        attr_dict = {
                            'name': attribute_name,
                            'groupName': group_name
                        }
                        attributes.append(attr_dict)
                    elif 'answers' in classification.keys():
                        for attr in classification['answers']:
                            attribute_name = attr['value']
                            attr_dict = {
                                'name': attribute_name,
                                'groupName': group_name
                            }
                            attributes.append(attr_dict)

            sa_obj = {
                'className': class_name,
                'attributes': attributes,
                'probability': 100,
                'locked': False,
                'visible': True,
                'parts': []
            }

            if 'bbox' in instance.keys() or 'polygon' in instance.keys(
            ) or 'line' in instance.keys() or 'point' in instance.keys():
                continue

            image_downloader(instance['instanceURI'], mask_name)
            mask = cv2.imread(mask_name)
            if i == 0:
                H, W, C = mask.shape
                sa_mask = np.zeros((H, W, C + 1))
            sa_mask[np.all(mask == [255, 255, 255], axis=2)
                   ] = list(hex_to_rgb(blue_colors[i]))[::-1] + [255]

            sa_obj['parts'].append({'color': blue_colors[i]})
            sa_loader.append(sa_obj.copy())
            Path(mask_name).unlink()

        sa_jsons[file_name] = sa_loader
        sa_masks[mask_name] = sa_mask

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, sa_masks
