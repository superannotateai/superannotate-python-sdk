import cv2 as cv
from pycocotools import mask as cocomask
import numpy as np


def __instance_object_commons_per_instance(
    instance, id_generator, image_commons
):
    if "parts" not in instance:
        return None
    anno_id = next(id_generator)
    parts = [int(part["color"][1:], 16) for part in instance["parts"]]

    category_id = instance['classId']
    instance_bitmask = np.isin(image_commons.flat_mask, parts)
    size = instance_bitmask.shape[::-1]

    databytes = instance_bitmask * np.uint8(255)
    contours, hierarchy = cv.findContours(
        databytes, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE
    )
    coco_instance_mask = cocomask.encode(np.asfortranarray(instance_bitmask))

    bbox = cocomask.toBbox(coco_instance_mask).tolist()
    area = int(cocomask.area(coco_instance_mask))
    return (bbox, area, contours, category_id, anno_id)


def instance_object_commons(image_commons, id_generator):
    sa_ann_json = image_commons.sa_ann_json
    commons_lst = [
        __instance_object_commons_per_instance(x, id_generator, image_commons)
        for x in sa_ann_json
    ]
    return commons_lst


def sa_pixel_to_coco_object_detection(
    make_annotation, image_commons, id_generator
):
    commons_lst = instance_object_commons(image_commons, id_generator)
    annotations_per_image = []
    image_info = image_commons.image_info
    for common in commons_lst:

        bbox, area, contours, category_id, anno_id = common
        segmentation = [
            [
                bbox[0], bbox[1], bbox[0], bbox[1] + bbox[3], bbox[0] + bbox[2],
                bbox[1] + bbox[3], bbox[0] + bbox[2], bbox[1]
            ]
        ]

        annotations_per_image.append(
            make_annotation(
                category_id, image_info['id'], bbox, segmentation, area, anno_id
            )
        )

    return (image_info, annotations_per_image)


def sa_pixel_to_coco_instance_segmentation(
    make_annotation, image_commons, id_generator
):
    commons_lst = instance_object_commons(image_commons, id_generator)
    image_info = image_commons.image_info
    annotations_per_image = []
    for common in commons_lst:
        if common is None:
            continue
        bbox, area, contours, category_id, anno_id = common
        if category_id < 0:
            continue
        segmentation = [
            contour.flatten().tolist()
            for contour in contours if len(contour.flatten().tolist()) >= 5
        ]

        annotations_per_image.append(
            make_annotation(
                category_id, image_info['id'], bbox, segmentation, area, anno_id
            )
        )

    return (image_info, annotations_per_image)


def sa_pixel_to_coco_panoptic_segmentation(image_commons, id_generator):

    sa_ann_json = image_commons.sa_ann_json
    flat_mask = image_commons.flat_mask
    ann_mask = image_commons.ann_mask

    segments_info = []

    for instance in sa_ann_json:

        if 'parts' not in instance:
            continue

        parts = [int(part['color'][1:], 16) for part in instance['parts']]
        if instance['classId'] <0:
            continue
        category_id = instance['classId']
        instance_bitmask = np.isin(flat_mask, parts)
        segment_id = next(id_generator)
        ann_mask[instance_bitmask] = segment_id
        coco_instance_mask = cocomask.encode(
            np.asfortranarray(instance_bitmask)
        )
        bbox = cocomask.toBbox(coco_instance_mask).tolist()
        area = int(cocomask.area(coco_instance_mask))

        segment_info = {
            'id': segment_id,
            'category_id': category_id,
            'area': area,
            'bbox': bbox,
            'iscrowd': 0
        }

        segments_info.append(segment_info)

    return (image_commons.image_info, segments_info, image_commons.ann_mask)
