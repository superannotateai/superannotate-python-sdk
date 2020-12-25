import json

import cv2
import numpy as np

from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

from superannotate.pycocotools_sa.coco import COCO
from superannotate.pycocotools_sa import mask as maskUtils

import time

from ....common import id2rgb

from ..sa_json_helper import _create_vector_instance


def _rle_to_polygon(coco_json, annotation):
    coco = COCO(coco_json)
    # start = time.time()
    binary_mask = coco.annToMask(annotation)
    # stop = time.time()
    # intervals.append(stop - start)
    contours, _ = cv2.findContours(
        binary_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    segmentation = []

    for contour in contours:
        contour = contour.flatten().tolist()
        if len(contour) > 4:
            segmentation.append(contour)
        if len(segmentation) == 0:
            continue
    return segmentation


def coco_instance_segmentation_to_sa_vector(coco_path, images_path):
    coco_json = json.load(open(coco_path))
    cat_id_to_cat = {}
    for cat in coco_json['categories']:
        cat_id_to_cat[cat['id']] = cat

    instance_groups = {}
    for annot in coco_json['annotations']:
        if 'id' in annot:
            if annot['id'] in instance_groups:
                instance_groups[annot['id']] += 1
            else:
                instance_groups[annot['id']] = 1

    image_id_to_annotations = {}
    for annot in tqdm(coco_json['annotations'], "Converting annotations"):
        if isinstance(annot['segmentation'], dict):
            if isinstance(annot['segmentation']['counts'], list):
                annot['segmentation'] = _rle_to_polygon(coco_path, annot)
            else:
                binary_mask = maskUtils.decode(annot['segmentation'])
                contours, _ = cv2.findContours(
                    binary_mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                segments = []
                for contour in contours:
                    contour = contour.flatten().tolist()
                    if len(contour) > 4:
                        segments.append(contour)
                annot['segmentation'] = segments

        cat = cat_id_to_cat[annot['category_id']]
        sa_loader = []
        groupid = 0
        for polygon in annot['segmentation']:
            if 'id' in annot and annot[
                'id'] in instance_groups and instance_groups[annot['id']] > 1:
                groupid = annot['id']

            sa_obj = _create_vector_instance(
                'polygon', polygon, {}, [], cat['name']
            )
            if groupid != 0:
                sa_obj['groupId'] = groupid

            if annot['image_id'] not in image_id_to_annotations:
                image_id_to_annotations[annot['image_id']] = [sa_obj]
            else:
                image_id_to_annotations[annot['image_id']].append(sa_obj)

    sa_jsons = {}
    for img in tqdm(coco_json['images'], "Writing annotations to disk"):
        if 'file_name' in img:
            image_path = Path(img['file_name']).name
        else:
            image_path = img['coco_url'].split('/')[-1]

        if img['id'] not in image_id_to_annotations:
            sa_loader = []
        else:
            sa_loader = image_id_to_annotations[img['id']]
        file_name = image_path + "___objects.json"
        sa_jsons[file_name] = sa_loader
    return sa_jsons


def coco_object_detection_to_sa_vector(coco_path, images_path):
    coco_json = json.load(open(coco_path))
    cat_id_to_cat = {}
    for cat in coco_json['categories']:
        cat_id_to_cat[cat['id']] = cat

    image_id_to_annotations = {}
    for annot in tqdm(coco_json['annotations'], "Converting annotations"):
        if isinstance(annot['segmentation'], dict):
            if isinstance(annot['segmentation']['counts'], list):
                annot['segmentation'] = _rle_to_polygon(coco_path, annot)
            else:
                binary_mask = maskUtils.decode(annot['segmentation'])
                contours, _ = cv2.findContours(
                    binary_mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                segments = []
                for contour in contours:
                    contour = contour.flatten().tolist()
                    if len(contour) > 4:
                        segments.append(contour)
                annot['segmentation'] = segments

        cat = cat_id_to_cat[annot['category_id']]

        points = (
            annot['bbox'][0], annot['bbox'][1],
            annot['bbox'][0] + annot['bbox'][2],
            annot['bbox'][1] + annot['bbox'][3]
        )

        sa_obj = _create_vector_instance('bbox', points, {}, [], cat['name'])

        if annot['image_id'] not in image_id_to_annotations:
            image_id_to_annotations[annot['image_id']] = [sa_obj]
        else:
            image_id_to_annotations[annot['image_id']].append(sa_obj)

    sa_jsons = {}
    for img in tqdm(coco_json['images'], "Writing annotations to disk"):
        if 'file_name' in img:
            image_path = Path(img['file_name']).name
        else:
            image_path = img['coco_url'].split('/')[-1]

        if img['id'] not in image_id_to_annotations:
            sa_loader = []
        else:
            sa_loader = image_id_to_annotations[img['id']]
        file_name = image_path + "___objects.json"
        sa_jsons[file_name] = sa_loader
    return sa_jsons


def coco_keypoint_detection_to_sa_vector(coco_path, images_path):
    coco_json = json.load(open(coco_path))
    loader = []

    cat_id_to_cat = {}
    for cat in coco_json["categories"]:
        cat_id_to_cat[cat["id"]] = {
            "name": cat["name"],
            "keypoints": cat["keypoints"],
            "skeleton": cat["skeleton"]
        }

    for annot in tqdm(coco_json['annotations'], 'Converting annotations'):
        if annot['num_keypoints'] > 0:
            sa_points = [
                item for index, item in enumerate(annot['keypoints'])
                if (index + 1) % 3 != 0
            ]

            sa_points = [
                (sa_points[i], sa_points[i + 1])
                for i in range(0, len(sa_points), 2)
            ]
            if annot["category_id"] in cat_id_to_cat.keys():
                keypoint_names = cat_id_to_cat[annot["category_id"]
                                              ]['keypoints']

                sa_template = {
                    'type': 'template',
                    'classId': annot['category_id'],
                    'probability': 100,
                    'points': [],
                    'connections': [],
                    'attributes': [],
                    'attributeNames': [],
                    'pointLabels': {},
                    'locked': False,
                    'visible': True,
                    'templateId': -1,
                    'className': cat_id_to_cat[annot["category_id"]]["name"],
                    'templateName': 'skeleton',
                    'imageId': annot['image_id']
                }

                bad_points = []
                id_mapping = {}
                index = 1
                for point_index, point in enumerate(sa_points):
                    if sa_points[point_index] == (0, 0):
                        bad_points.append(point_index + 1)
                        continue
                    id_mapping[point_index + 1] = index
                    sa_template['points'].append(
                        {
                            'id': index,
                            'x': point[0],
                            'y': point[1]
                        }
                    )
                    index += 1

                for connection in cat_id_to_cat[annot["category_id"]
                                               ]['skeleton']:

                    index = cat['skeleton'].index(connection)
                    from_point = cat_id_to_cat[annot["category_id"]
                                              ]['skeleton'][index][0]
                    to_point = cat_id_to_cat[annot["category_id"]
                                            ]['skeleton'][index][1]

                    if from_point in bad_points or to_point in bad_points:
                        continue

                    sa_template['connections'].append(
                        {
                            'id': index + 1,
                            'from': id_mapping[from_point],
                            'to': id_mapping[to_point]
                        }
                    )

                for kp_index, kp_name in enumerate(keypoint_names):
                    if kp_index + 1 in bad_points:
                        continue
                    sa_template['pointLabels'][id_mapping[kp_index + 1] -
                                               1] = kp_name

                for img in coco_json['images']:
                    if sa_template['imageId'] == img['id']:
                        loader.append((img['id'], sa_template))

        sa_jsons = {}
        for img in coco_json['images']:
            f_loader = []
            for img_id, img_data in loader:
                if img['id'] == img_id:
                    f_loader.append(img_data)
            file_name = str(Path(img['file_name']).name) + "___objects.json"
            sa_jsons[file_name] = f_loader
    return sa_jsons
