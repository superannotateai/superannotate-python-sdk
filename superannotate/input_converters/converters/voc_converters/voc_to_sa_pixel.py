import cv2
from tqdm import tqdm
import numpy as np

from .voc_helper import (_get_voc_instances_from_xml, _create_classes, _iou)

from ..sa_json_helper import _create_pixel_instance

from ....common import hex_to_rgb, blue_color_generator


def _generate_polygons(object_mask_path, class_mask_path):
    segmentation = []

    object_mask = cv2.imread(str(object_mask_path), cv2.IMREAD_GRAYSCALE)
    class_mask = cv2.imread(str(class_mask_path), cv2.IMREAD_GRAYSCALE)

    object_unique_colors = np.unique(object_mask)

    num_colors = len([i for i in object_unique_colors if i not in (0, 220)])
    bluemask_colors = blue_color_generator(num_colors)
    H, W = object_mask.shape
    sa_mask = np.zeros((H, W, 4))
    i = 0
    for unique_color in object_unique_colors:
        if unique_color in (0, 220):
            continue

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
            segmentation.append(segment)
        if len(segmentation) == 0:
            continue

        sa_mask[object_mask == unique_color
               ] = [255] + list(hex_to_rgb(bluemask_colors[i]))
        i += 1
    return segmentation, sa_mask, bluemask_colors


def _generate_instances(polygon_instances, voc_instances, bluemask_colors):
    instances = []
    i = 0
    for polygon in polygon_instances:
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
                "polygon": polygon,
                "bbox": voc_instances[ind][1],
                "blue_color": bluemask_colors[i]
            }
        )
        i += 1
    return instances


def voc_instance_segmentation_to_sa_pixel(voc_root):
    classes = []
    object_masks_dir = voc_root / 'SegmentationObject'
    class_masks_dir = voc_root / 'SegmentationClass'
    annotation_dir = voc_root / "Annotations"

    sa_jsons = {}
    sa_masks = {}
    for filename in object_masks_dir.glob('*'):
        polygon_instances, sa_mask, bluemask_colors = _generate_polygons(
            object_masks_dir / filename.name,
            class_masks_dir / filename.name,
        )
        voc_instances = _get_voc_instances_from_xml(
            annotation_dir / filename.name
        )
        maped_instances = _generate_instances(
            polygon_instances, voc_instances, bluemask_colors
        )

        sa_loader = []
        for instance in maped_instances:
            parts = [{"color": instance["blue_color"]}]
            sa_obj = _create_pixel_instance(parts, [], instance["className"])
            sa_loader.append(sa_obj)
            classes.append(instance['className'])

        sa_file_name = filename.stem + ".jpg___pixel.json"
        sa_jsons[sa_file_name] = sa_loader

        sa_mask_name = filename.stem + ".jpg___save.png"
        sa_masks[sa_mask_name] = sa_mask

    classes = _create_classes(classes)
    return (classes, sa_jsons, sa_masks)
