import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

from ..common import blue_color_generator, hex_to_rgb
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")


def _merge_jsons(input_dir, output_dir):
    cat_id_map = {}
    classes_json = json.load(open(input_dir / "classes" / "classes.json"))

    new_classes = []
    for idx, class_ in enumerate(classes_json):
        cat_id_map[class_["id"]] = idx + 2
        class_["id"] = idx + 2
        new_classes.append(class_)

    files = input_dir.glob("*.json")
    merged_json = {}
    files_path = []
    (output_dir / 'images' / 'thumb').mkdir(parents=True)
    for f in tqdm(files, "Merging files"):
        json_data = json.load(open(f))
        meta = {
            "type": "meta",
            "name": "lastAction",
            "timestamp": int(round(time.time() * 1000))
        }
        for js_data in json_data:
            if "classId" in js_data:
                js_data["classId"] = cat_id_map[js_data["classId"]]
        json_data.append(meta)
        file_name = str(f.name).replace("___objects.json", "")
        merged_json[file_name] = json_data

        files_path.append(
            {
                'srcPath':
                    str(output_dir.resolve() / file_name),
                'name':
                    file_name,
                'imagePath':
                    str(output_dir.resolve() / file_name),
                'thumbPath':
                    str(
                        output_dir.resolve() / 'images' / 'thumb' /
                        ('thmb_' + file_name + '.jpg')
                    ),
                'valid':
                    True
            }
        )
        copy_file(input_dir / file_name, output_dir / 'images' / file_name)

        img = Image.open(output_dir / 'images' / file_name)
        img.thumbnail((168, 120), Image.ANTIALIAS)
        img.save(
            output_dir / 'images' / 'thumb' / ('thmb_' + file_name + '.jpg')
        )

    with open(output_dir / 'images' / 'images.sa', 'w') as fw:
        fw.write(json.dumps(files_path))

    with open(output_dir / 'config.json', 'w') as fw:
        json.dump({"pathSeparator": os.sep, "os": sys.platform}, fw)

    with open(output_dir / "annotations.json", "w") as final_json_file:
        json.dump(merged_json, final_json_file, indent=2)

    with open(output_dir / "classes.json", "w") as fw:
        json.dump(classes_json, fw, indent=2)


def _split_json(input_dir, output_dir):
    output_dir.mkdir(parents=True)
    json_data = json.load(open(input_dir / "annotations.json"))
    for img, annotations in tqdm(json_data.items(), 'Splitting files'):
        objects = []
        for annot in annotations:
            if 'type' in annot.keys() and annot['type'] != 'meta':
                objects.append(annot)
        copy_file(input_dir / 'images' / img, output_dir / img)
        with open(output_dir / (img + "___objects.json"), "w") as fw:
            json.dump(objects, fw, indent=2)

    (output_dir / "classes").mkdir(parents=True)
    copy_file(
        input_dir / "classes.json", output_dir / "classes" / "classes.json"
    )


def copy_file(src_path, dst_path):
    shutil.copy(src_path, dst_path)


def sa_convert_platform(input_dir, output_dir, input_platform):
    if input_platform == "Web":
        for file_name in os.listdir(input_dir):
            if '___pixel.json' in file_name:
                raise SABaseException(
                    0, "Desktop platform doesn't support 'Pixel' projects"
                )
        _merge_jsons(input_dir, output_dir)
    elif input_platform == 'Desktop':
        _split_json(input_dir, output_dir)


def from_pixel_to_vector(json_paths):
    sa_jsons = {}
    for json_path in json_paths:
        file_name = str(json_path.name
                       ).replace('___pixel.json', '___objects.json')

        mask_name = str(json_path).replace('___pixel.json', '___save.png')
        img = cv2.imread(mask_name)
        H, W, _ = img.shape

        sa_loader = []
        instances = json.load(open(json_path))
        idx = 0
        for instance in instances:
            if 'parts' not in instance.keys():
                if 'type' in instance.keys() and instance['type'] == 'meta':
                    sa_loader.append(instance)
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
                    sa_loader.append(temp.copy())
                    temp['type'] = 'bbox'
                    temp['points'] = {
                        'x1': min(polygon[::2]),
                        'x2': max(polygon[::2]),
                        'y1': min(polygon[1::2]),
                        'y2': max(polygon[1::2])
                    }
                    sa_loader.append(temp.copy())

        sa_jsons[file_name] = {'json': sa_loader, 'mask': None}
    return sa_jsons


def from_vector_to_pixel(json_paths):
    sa_jsons = {}
    for json_path in json_paths:
        file_name = str(json_path.name
                       ).replace('___objects.json', '___pixel.json')

        img_name = str(json_path).replace('___objects.json', '')
        img = cv2.imread(img_name)
        H, W, _ = img.shape

        mask = np.zeros((H, W, 4))
        sa_loader = []

        instances = json.load(open(json_path))
        blue_colors = blue_color_generator(len(instances))
        instances_group = {}
        for idx, instance in enumerate(instances):
            if instance['type'] == 'polygon':
                if instance['groupId'] in instances_group.keys():
                    instances_group[instance['groupId']].append(instance)
                else:
                    instances_group[instance['groupId']] = [instance]
            elif instance['type'] == 'meta':
                sa_loader.append(instance)

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
                    sa_loader.append(instance.copy())
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
                sa_loader.append(instance.copy())

        sa_jsons[file_name] = {'json': sa_loader, 'mask': mask}

    return sa_jsons


def sa_convert_project_type(input_dir, output_dir):
    json_generator = input_dir.glob('*.json')
    json_paths = list(json_generator)

    extension = ''
    if '___pixel.json' in json_paths[0].name:
        sa_jsons = from_pixel_to_vector(json_paths)
        extension = '___objects.json'
    elif '__objects.json' in json_paths[0].name:
        sa_jsons = from_vector_to_pixel(json_paths)
        extension = '___pixel.json'
    else:
        raise SABaseException(
            0,
            "'input_dir' should contain JSON files with '[IMAGE_NAME]___objects.json'  or '[IMAGE_NAME]___pixel.json' names structure."
        )

    output_dir.joinpath('classes').mkdir(parents=True)
    shutil.copy(
        input_dir.joinpath('classes', 'classes.json'),
        output_dir.joinpath('classes', 'classes.json')
    )

    for key, value in sa_jsons.items():
        with open(output_dir.joinpath(key), 'w') as fw:
            json.dump(value['json'], fw, indent=2)
        file_name = key.replace(extension, '')
        shutil.copy(
            input_dir.joinpath(file_name), output_dir.joinpath(file_name)
        )

        if value['mask'] is not None:
            mask_name = key.replace(extension, '___save.png')
            cv2.imwrite(str(output_dir.joinpath(mask_name)), value['mask'])


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
