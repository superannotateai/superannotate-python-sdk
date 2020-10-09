import os
import cv2
import json
from tqdm import tqdm
import numpy as np
import xml.etree.ElementTree as ET

from ....common import hex_to_rgb, blue_color_generator


# Generates polygons for each instance
def _generate_polygons(object_mask_path, class_mask_path):
    segmentation = []

    object_mask = cv2.imread(object_mask_path, cv2.IMREAD_GRAYSCALE)
    class_mask = cv2.imread(class_mask_path, cv2.IMREAD_GRAYSCALE)

    object_unique_colors = np.unique(object_mask)

    num_colors = len([i for i in object_unique_colors if i != 0 and i != 220])
    bluemask_colors = blue_color_generator(num_colors)
    H, W = object_mask.shape
    sa_mask = np.zeros((H, W, 4))
    i = 0
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
            for contour in contours:
                contour = contour.flatten().tolist()
                segment += contour
            if len(contour) > 4:
                segmentation.append((segment, int(class_color)))
            if len(segmentation) == 0:
                continue
        sa_mask[object_mask == unique_color
               ] = [255] + list(hex_to_rgb(bluemask_colors[i]))
        i += 1
    return segmentation, sa_mask, bluemask_colors


def _iou(bbox1, bbox2):
    xmin1, ymin1, xmax1, ymax1 = bbox1
    xmin2, ymin2, xmax2, ymax2 = bbox2

    x = max(0, min(xmax1, xmax2) - max(xmin1, xmin2))
    y = max(0, min(ymax1, ymax2) - max(ymin1, ymin2))
    return x * y / float(
        (xmax1 - xmin1) * (ymax1 - ymin1) + (xmax2 - xmin2) *
        (ymax2 - ymin2) - x * y
    )


def _generate_instances(ploygon_instances, voc_instances, bluemask_colors):
    instances = []
    i = 0
    for polygon, color_id in ploygon_instances:
        ious = []
        bbox_poly = [
            min(polygon[::2]),
            min(polygon[1::2]),
            max(polygon[::2]),
            max(polygon[1::2])
        ]
        for class_name, bbox in voc_instances:
            ious.append(_iou(bbox_poly, bbox))
        ind = np.argmax(ious)
        instances.append(
            {
                "className": voc_instances[ind][0],
                "classId": color_id,
                "polygon": polygon,
                "bbox": voc_instances[ind][1],
                "blue_color": bluemask_colors[i]
            }
        )
        i += 1
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


def voc_instance_segmentation_to_sa_pixel(voc_root):
    classes = {}
    object_masks_dir = os.path.join(voc_root, 'SegmentationObject')
    class_masks_dir = os.path.join(voc_root, 'SegmentationClass')
    annotation_dir = os.path.join(os.path.join(voc_root, "Annotations"))

    sa_jsons = {}
    sa_masks = {}
    for filename in tqdm(os.listdir(object_masks_dir)):
        polygon_instances, sa_mask, bluemask_colors = _generate_polygons(
            os.path.join(object_masks_dir, filename),
            os.path.join(class_masks_dir, filename)
        )
        voc_instances = _get_voc_instances_from_xml(
            os.path.join(annotation_dir, filename)
        )
        maped_instances = _generate_instances(
            polygon_instances, voc_instances, bluemask_colors
        )

        sa_loader = []
        for instance in maped_instances:
            sa_polygon = {
                'classId': instance["classId"],
                'className': instance["className"],
                'parts': [{
                    "color": instance["blue_color"]
                }],
                'attributes': [],
                'probability': 100,
                'locked': False,
                'visible': True,
            }
            sa_loader.append(sa_polygon)
            if instance["className"] not in classes.keys():
                classes[instance["className"]] = instance["classId"]

        sa_file_name = os.path.splitext(filename)[0] + ".jpg___pixel.json"
        sa_jsons[sa_file_name] = sa_loader

        sa_mask_name = os.path.splitext(filename)[0] + ".jpg___save.png"
        sa_masks[sa_mask_name] = sa_mask

    classes = _create_classes(classes)
    return (classes, sa_jsons, sa_masks)
