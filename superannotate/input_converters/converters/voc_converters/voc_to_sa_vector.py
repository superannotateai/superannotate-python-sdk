import os
import cv2
import json
import numpy as np
import xml.etree.ElementTree as ET
from tqdm import tqdm


def _generate_polygons(object_mask_path, class_mask_path):
    segmentation = []

    object_mask = cv2.imread(str(object_mask_path), cv2.IMREAD_GRAYSCALE)
    class_mask = cv2.imread(str(class_mask_path), cv2.IMREAD_GRAYSCALE)

    object_unique_colors = np.unique(object_mask)

    index = 1
    groupId = 0
    for unique_color in object_unique_colors:
        if unique_color == 0 or unique_color == 220:
            continue
        else:
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

            segmentation.append((segment, groupId))

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
    for polygon, group_id in polygon_instances:
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
        for _, bbox in voc_instances:
            ious.append(_iou(bbox_poly, bbox))
        ind = np.argmax(ious)
        for poly in polygon:
            class_name = list(voc_instances[ind][0].keys())[0]
            attributes = voc_instances[ind][0][class_name]
            instances.append(
                {
                    'className': class_name,
                    'polygon': poly,
                    'bbox': voc_instances[ind][1],
                    'groupId': group_id,
                    'classAttributes': attributes
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
        class_attributes = []
        for attr in ['pose', 'occluded', 'difficult', 'truncated']:
            attr_value = instance.find(attr)
            if attr_value is not None:
                class_attributes.append(
                    {
                        'name': attr_value.text,
                        'groupName': attr
                    }
                )

        bbox = instance.find("bndbox")
        bbox = [
            float(bbox.find(x).text) for x in ["xmin", "ymin", "xmax", "ymax"]
        ]
        voc_instances.append(({class_name: class_attributes}, bbox))
    return voc_instances


def _create_classes(voc_instance):
    classes = {}
    for instance in voc_instance:
        for class_, value in instance.items():
            if class_ not in classes:
                classes[class_] = {}

            for attr in value:
                if attr['groupName'] in classes[class_]:
                    classes[class_][attr['groupName']].append(attr['name'])
                else:
                    classes[class_][attr['groupName']] = [attr['name']]

    sa_classes = []
    for class_ in classes:
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        attribute_groups = []
        for attr_group, value in classes[class_].items():
            attributes = []
            for attr in set(value):
                attributes.append({'name': attr})

            attribute_groups.append(
                {
                    'name': attr_group,
                    'is_multiselect': 0,
                    'attributes': attributes
                }
            )
        sa_class = {
            "name": class_,
            "color": hexcolor,
            "attribute_groups": attribute_groups
        }
        sa_classes.append(sa_class)
    return sa_classes


def voc_instance_segmentation_to_sa_vector(voc_root, output_dir):
    classes = []
    object_masks_dir = voc_root / 'SegmentationObject'
    class_masks_dir = voc_root / 'SegmentationClass'
    annotation_dir = voc_root / "Annotations"

    file_list = object_masks_dir.glob('*')
    sa_jsons = {}
    for filename in tqdm(file_list):
        polygon_instances = _generate_polygons(
            object_masks_dir / filename.name, class_masks_dir / filename.name
        )
        voc_instances = _get_voc_instances_from_xml(
            annotation_dir / filename.name
        )
        for class_, _ in voc_instances:
            classes.append(class_)

        maped_instances = _generate_instances(polygon_instances, voc_instances)
        sa_loader = []
        for instance in maped_instances:
            sa_polygon = {
                'type': 'polygon',
                'points': instance["polygon"],
                'className': instance["className"],
                'attributes': instance['classAttributes'],
                'probability': 100,
                'locked': False,
                'visible': True,
                'groupId': instance['groupId']
            }
            sa_loader.append(sa_polygon)

        sa_file_name = os.path.splitext(filename.name
                                       )[0] + ".jpg___objects.json"
        sa_jsons[sa_file_name] = sa_loader

    classes = _create_classes(classes)
    return (classes, sa_jsons)


def voc_object_detection_to_sa_vector(voc_root, output_dir):
    classes = []
    annotation_dir = voc_root / "Annotations"
    files_list = annotation_dir.glob('*')
    sa_jsons = {}
    for filename in tqdm(files_list):
        voc_instances = _get_voc_instances_from_xml(
            annotation_dir / filename.name
        )
        sa_loader = []
        for class_, bbox in voc_instances:
            class_name = list(class_.keys())[0]
            classes.append(class_)

            sa_bbox = {
                'type': "bbox",
                'className': class_name,
                'probability': 100,
                'points': [],
                'attributes': class_[class_name],
                'points':
                    {
                        "x1": bbox[0],
                        "y1": bbox[1],
                        "x2": bbox[2],
                        "y2": bbox[3]
                    }
            }
            sa_loader.append(sa_bbox)

        sa_file_name = os.path.splitext(filename.name
                                       )[0] + ".jpg___objects.json"
        sa_jsons[sa_file_name] = sa_loader

    classes = _create_classes(classes)
    return (classes, sa_jsons)
