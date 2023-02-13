"""
VOC to SA conversion method
"""
import logging
import threading

import cv2
import numpy as np

from ....common import blue_color_generator
from ....common import hex_to_rgb
from ....common import tqdm_converter
from ....common import write_to_json
from ..sa_json_helper import _create_pixel_instance
from ..sa_json_helper import _create_sa_json
from .voc_helper import _get_image_shape_from_xml
from .voc_helper import _get_voc_instances_from_xml
from .voc_helper import _iou

logger = logging.getLogger("sa")


def _generate_polygons(object_mask_path):
    segmentation = []

    object_mask = cv2.imread(str(object_mask_path), cv2.IMREAD_GRAYSCALE)

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
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        segment = []
        for contour in contours:
            contour = contour.flatten().tolist()
            segment += contour
        if len(contour) > 4:
            segmentation.append(segment)
        if len(segmentation) == 0:
            continue

        sa_mask[object_mask == unique_color] = [255] + list(
            hex_to_rgb(bluemask_colors[i])
        )
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
            max(polygon[1::2]),
        ]
        for _, bbox in voc_instances:
            ious.append(_iou(bbox_poly, bbox))
        ind = np.argmax(ious)
        class_name = list(voc_instances[ind][0].keys())[0]
        attributes = voc_instances[ind][0][class_name]
        instances.append(
            {
                "className": class_name,
                "polygon": polygon,
                "bbox": voc_instances[ind][1],
                "blue_color": bluemask_colors[i],
                "classAttributes": attributes,
            }
        )
        i += 1
    return instances


def voc_instance_segmentation_to_sa_pixel(voc_root, output_dir):
    classes = []
    object_masks_dir = voc_root / "SegmentationObject"
    annotation_dir = voc_root / "Annotations"

    file_list = list(object_masks_dir.glob("*"))
    if not file_list:
        logger.warning(
            "You need to have both 'Annotations' and 'SegmentationObject' directories to be able to convert."
        )
    images_converted = []
    images_not_converted = []
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=tqdm_converter,
        args=(len(file_list), images_converted, images_not_converted, finish_event),
        daemon=True,
    )
    logger.info("Converting to SuperAnnotate JSON format")
    tqdm_thread.start()
    for filename in file_list:
        polygon_instances, sa_mask, bluemask_colors = _generate_polygons(
            object_masks_dir / filename.name
        )
        voc_instances = _get_voc_instances_from_xml(annotation_dir / filename.name)
        for class_, _ in voc_instances:
            classes.append(class_)

        maped_instances = _generate_instances(
            polygon_instances, voc_instances, bluemask_colors
        )

        sa_instances = []
        for instance in maped_instances:
            parts = [{"color": instance["blue_color"]}]
            sa_obj = _create_pixel_instance(
                parts, instance["classAttributes"], instance["className"]
            )
            sa_instances.append(sa_obj)

        images_converted.append(filename)
        file_name = "%s.jpg___pixel.json" % (filename.stem)
        height, width = _get_image_shape_from_xml(annotation_dir / filename.name)
        sa_metadata = {"name": filename.stem, "height": height, "width": width}
        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)

        mask_name = "%s.jpg___save.png" % (filename.stem)
        cv2.imwrite(str(output_dir / mask_name), sa_mask[:, :, ::-1])
    finish_event.set()
    tqdm_thread.join()
    return classes
