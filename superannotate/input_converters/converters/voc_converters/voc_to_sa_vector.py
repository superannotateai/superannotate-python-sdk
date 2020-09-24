import os
import cv2
import json
import numpy as np
import xml.etree.ElementTree as ET
from tqdm import tqdm


def _generate_polygons(object_mask_path, class_mask_path):
    segmentation = []

    object_mask = cv2.imread(object_mask_path, cv2.IMREAD_GRAYSCALE)
    class_mask = cv2.imread(class_mask_path, cv2.IMREAD_GRAYSCALE)

    object_unique_colors = np.unique(object_mask)

    index = 1
    groupId = 0
    for unique_color in object_unique_colors:
        if unique_color == 0 or unique_color == 220:
            continue
        else:
            class_color = class_mask[object_mask == unique_color][0]
            mask = np.zeros_like(object_mask)
            mask[object_mask == unique_color] = 255
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            segment = []
            if len(contours) > 1:
                for contour in contours:
                    segment.append(contour.flatten().tolist())
                groupId = index
                index += 1
            else:
                segment.append(contours[0].flatten().tolist())
                groupId = 0

            segmentation.append((segment, int(class_color), groupId))

    return segmentation


def _iou(bbox1, bbox2):
    xmin1, ymin1, xmax1, ymax1 = bbox1
    xmin2, ymin2, xmax2, ymax2 = bbox2

    x = max(0, min(xmax1, xmax2) - max(xmin1, xmin2))
    y = max(0, min(ymax1, ymax2) - max(ymin1, ymin2))
    return x * y / float(
        (xmax1 - xmin1) * (ymax1 - ymin1) + (xmax2 - xmin2) *
        (ymax2 - ymin2) - x * y
    )


def _generate_instances(polygon_instances, voc_instances):
    instances = []
    for polygon, color_id, group_id in polygon_instances:
        ious = []
        if len(polygon) > 1:
            temp = []
            for poly in polygon:
                temp += poly
        else:
            temp = polygon[0]
        bbox_poly = [
            min(temp[::2]),
            min(temp[1::2]),
            max(temp[::2]),
            max(temp[1::2])
        ]
        for class_name, bbox in voc_instances:
            ious.append(_iou(bbox_poly, bbox))
        ind = np.argmax(ious)
        for poly in polygon:
            instances.append(
                {
                    'className': voc_instances[ind][0],
                    'classId': color_id,
                    'polygon': poly,
                    'bbox': voc_instances[ind][1],
                    'groupId': group_id
                }
            )
    return instances


def _get_voc_instances_from_xml(file_path):
    with open(os.path.splitext(file_path)[0] + ".xml") as f:
        tree = ET.parse(f)
    instances = tree.findall('object')
    voc_instances = []
    for instance in instances:
        class_name = instance.find("name").text
        bbox = instance.find("bndbox")
        bbox = [
            float(bbox.find(x).text) for x in ["xmin", "ymin", "xmax", "ymax"]
        ]
        voc_instances.append((class_name, bbox))
    return voc_instances


def _create_classes(classes):
    sa_classes = []
    for class_, id_ in classes.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_class = {
            "id": id_,
            "name": class_,
            "color": hexcolor,
            "attribute_groups": []
        }
        sa_classes.append(sa_class)
    return sa_classes


def voc_instance_segmentation_to_sa_vector(voc_root):
    classes = {}
    object_masks_dir = os.path.join(voc_root, 'SegmentationObject')
    class_masks_dir = os.path.join(voc_root, 'SegmentationClass')
    annotation_dir = os.path.join(voc_root, "Annotations")

    file_list = os.listdir(object_masks_dir)
    sa_jsons = {}
    for filename in tqdm(file_list):
        polygon_instances = _generate_polygons(
            os.path.join(object_masks_dir, filename),
            os.path.join(class_masks_dir, filename)
        )
        voc_instances = _get_voc_instances_from_xml(
            os.path.join(annotation_dir, filename)
        )
        maped_instances = _generate_instances(polygon_instances, voc_instances)
        sa_loader = []
        for instance in maped_instances:
            sa_polygon = {
                'type': 'polygon',
                'points': instance["polygon"],
                'classId': instance["classId"],
                'className': instance["className"],
                'attributes': [],
                'probability': 100,
                'locked': False,
                'visible': True,
                'groupId': instance['groupId']
            }
            sa_loader.append(sa_polygon)

            if instance["className"] not in classes.keys():
                classes[instance["className"]] = instance["classId"]

        sa_file_name = os.path.splitext(filename)[0] + ".jpg___objects.json"
        sa_jsons[sa_file_name] = sa_loader

    classes = _create_classes(classes)
    return (classes, sa_jsons, None)


def voc_object_detection_to_sa_vector(voc_root):
    classes = {}
    id_ = 1
    annotation_dir = os.path.join(os.path.join(voc_root, "Annotations"))
    files_list = os.listdir(annotation_dir)
    sa_jsons = {}
    for filename in tqdm(files_list):
        voc_instances = _get_voc_instances_from_xml(
            os.path.join(annotation_dir, filename)
        )
        sa_loader = []
        for class_name, bbox in voc_instances:
            if class_name not in classes.keys():
                classes[class_name] = id_
                id_ += 1

            sa_bbox = {
                'type': "bbox",
                'classId': classes[class_name],
                'className': class_name,
                'probability': 100,
                'points': [],
                'attributes': [],
                'points':
                    {
                        "x1": bbox[0],
                        "y1": bbox[1],
                        "x2": bbox[2],
                        "y2": bbox[3]
                    }
            }
            sa_loader.append(sa_bbox)

        sa_file_name = os.path.splitext(filename)[0] + ".jpg___objects.json"
        sa_jsons[sa_file_name] = sa_loader

    classes = _create_classes(classes)
    return (classes, sa_jsons, None)
