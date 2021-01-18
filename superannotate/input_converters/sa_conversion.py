'''
'''
import json
import logging
import shutil
from pathlib import Path

import cv2
import numpy as np

from ..common import (blue_color_generator, hex_to_rgb, write_to_json)
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")


def copy_file(src_path, dst_path):
    shutil.copy(src_path, dst_path)


def from_pixel_to_vector(json_paths, output_dir):
    img_names = []
    for json_path in json_paths:
        file_name = str(json_path.name
                       ).replace('___pixel.json', '___objects.json')

        mask_name = str(json_path).replace('___pixel.json', '___save.png')
        img = cv2.imread(mask_name)
        H, W, _ = img.shape

        sa_json = json.load(open(json_path))
        instances = sa_json['instances']
        idx = 0
        sa_instances = []
        for instance in instances:
            if 'parts' not in instance.keys():
                if 'type' in instance.keys() and instance['type'] == 'meta':
                    sa_instances.append(instance)
                continue

            parts = instance['parts']

            polygons = []
            for part in parts:
                color = list(hex_to_rgb(part['color']))
                mask = np.zeros((H, W), dtype=np.uint8)
                mask[np.all((img == color[::-1]), axis=2)] = 255
                contours, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                part_polygons = []
                for contour in contours:
                    segment = contour.flatten().tolist()
                    if len(segment) > 6:
                        part_polygons.append(segment)
                polygons.append(part_polygons)

            for part_polygons in polygons:
                if len(part_polygons) > 1:
                    idx += 1
                    group_id = idx
                else:
                    group_id = 0

                for polygon in part_polygons:
                    temp = instance.copy()
                    del temp['parts']
                    temp['pointLabels'] = {}
                    temp['groupId'] = group_id
                    temp['type'] = 'polygon'
                    temp['points'] = polygon
                    sa_instances.append(temp.copy())
                    temp['type'] = 'bbox'
                    temp['points'] = {
                        'x1': min(polygon[::2]),
                        'x2': max(polygon[::2]),
                        'y1': min(polygon[1::2]),
                        'y2': max(polygon[1::2])
                    }
                    sa_instances.append(temp.copy())

        sa_json['instances'] = sa_instances
        write_to_json(output_dir / file_name, sa_json)
        img_names.append(file_name.replace('___objects.json', ''))
    return img_names


def from_vector_to_pixel(json_paths, output_dir):
    img_names = []
    for json_path in json_paths:
        file_name = str(json_path.name
                       ).replace('___objects.json', '___pixel.json')

        img_name = str(json_path).replace('___objects.json', '')
        img = cv2.imread(img_name)
        H, W, _ = img.shape

        sa_json = json.load(open(json_path))
        instances = sa_json['instances']
        mask = np.zeros((H, W, 4))

        sa_instances = []
        blue_colors = blue_color_generator(len(instances))
        instances_group = {}
        for idx, instance in enumerate(instances):
            if instance['type'] == 'polygon':
                if instance['groupId'] in instances_group.keys():
                    instances_group[instance['groupId']].append(instance)
                else:
                    instances_group[instance['groupId']] = [instance]
            elif instance['type'] == 'meta':
                sa_instances.append(instance)

        idx = 0
        for key, instances in instances_group.items():
            if key == 0:
                for instance in instances:
                    pts = np.array(
                        [
                            instance['points'][2 * i:2 * (i + 1)]
                            for i in range(len(instance['points']) // 2)
                        ],
                        dtype=np.int32
                    )
                    bitmask = np.zeros((H, W))
                    cv2.fillPoly(bitmask, [pts], 1)
                    mask[bitmask == 1
                        ] = list(hex_to_rgb(blue_colors[idx]))[::-1] + [255]
                    del instance['type']
                    del instance['points']
                    del instance['pointLabels']
                    del instance['groupId']
                    instance['parts'] = [{'color': blue_colors[idx]}]
                    sa_instances.append(instance.copy())
                    idx += 1
            else:
                parts = []
                for instance in instances:
                    pts = np.array(
                        [
                            instance['points'][2 * i:2 * (i + 1)]
                            for i in range(len(instance['points']) // 2)
                        ],
                        dtype=np.int32
                    )
                    bitmask = np.zeros((H, W))
                    cv2.fillPoly(bitmask, [pts], 1)
                    mask[bitmask == 1
                        ] = list(hex_to_rgb(blue_colors[idx]))[::-1] + [255]
                    parts.append({'color': blue_colors[idx]})
                    idx += 1
                del instance['type']
                del instance['points']
                del instance['pointLabels']
                del instance['groupId']
                instance['parts'] = parts
                sa_instances.append(instance.copy())

        mask_name = file_name.replace('___pixel.json', '___save.png')
        cv2.imwrite(str(output_dir.joinpath(mask_name)), mask)

        sa_json['instances'] = sa_instances
        write_to_json(output_dir / file_name, sa_json)
        img_names.append(file_name.replace('___pixel.json', ''))
    return img_names


def sa_convert_project_type(input_dir, output_dir):
    json_paths = list(input_dir.glob('*.json'))

    output_dir.joinpath('classes').mkdir(parents=True)
    copy_file(
        input_dir.joinpath('classes', 'classes.json'),
        output_dir.joinpath('classes', 'classes.json')
    )

    if '___pixel.json' in json_paths[0].name:
        img_names = from_pixel_to_vector(json_paths, output_dir)
    elif '__objects.json' in json_paths[0].name:
        img_names = from_vector_to_pixel(json_paths, output_dir)
    else:
        raise SABaseException(
            0,
            "'input_dir' should contain JSON files with '[IMAGE_NAME]___objects.json'  or '[IMAGE_NAME]___pixel.json' names structure."
        )

    for img_name in img_names:
        copy_file(input_dir.joinpath(img_name), output_dir.joinpath(img_name))


def split_coco(
    coco_json_path, image_dir, output_dir, dataset_list_name, ratio_list
):
    coco_json = json.load(open(coco_json_path))

    groups = {}
    for dataset_name in dataset_list_name:
        groups[dataset_name] = {
            'info': coco_json['info'],
            'licenses': coco_json['licenses'],
            'images': [],
            'annotations': [],
            'categories': coco_json['categories']
        }

    images = coco_json['images']
    np.random.shuffle(images)
    num_of_images = len(images)
    points = []
    total = 0
    for ratio in ratio_list:
        total += ratio
        point = total / 100 * num_of_images
        points.append(int(point))

    image_id_to_group_map = {}
    group_id = 0
    dataset_name = dataset_list_name[group_id]
    (output_dir / dataset_name).mkdir(parents=True)
    for i, image in enumerate(images):
        if i in points:
            group_id += 1
            dataset_name = dataset_list_name[group_id]
            (output_dir / dataset_name).mkdir()

        image_name = Path(image['file_name']).name
        copy_file(
            image_dir / image_name, output_dir / dataset_name / image_name
        )

        image_id_to_group_map[image['id']] = group_id
        groups[dataset_name]['images'].append(image)

    for annotation in coco_json['annotations']:
        dataset_name = dataset_list_name[image_id_to_group_map[
            annotation['image_id']]]
        groups[dataset_name]['annotations'].append(annotation)

    for file_name, value in groups.items():
        with open(output_dir / (file_name + '.json'), 'w') as fw:
            json.dump(value, fw, indent=2)
