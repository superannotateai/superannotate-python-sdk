import os
import cv2
import json
import numpy as np

# Generates polygons for each instance
def _generate_polygons(object_mask_path, class_mask_path):
    segmentation = []

    object_mask = cv2.imread(object_mask_path, cv2.IMREAD_GRAYSCALE)
    class_mask = cv2.imread(class_mask_path, cv2.IMREAD_GRAYSCALE)

    object_unique_colors = np.unique(object_mask)

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
            for contour in contours:
                contour = contour.flatten().tolist()
                if len(contour) > 4:
                    segmentation.append((contour, class_color))
                if len(segmentation) == 0:
                    continue
    return segmentation

# Converts VOC segmentation format to annotate.online's vector format
def voc_instance_segmentation_to_sa_pixel():
    classes = set()

    object_masks_dir = os.path.join(pvoc_folder, 'SegmentationObject')
    class_masks_dir = os.path.join(pvoc_folder, 'SegmentationClass')

    for filename in os.listdir(object_masks_dir):
        sa_loader = []

        ploygon_instances = _generate_polygons(
            os.path.join(object_masks_dir, filename),
            os.path.join(class_masks_dir, filename)
        )

        for polygon, color_id in ploygon_instances:
            classes.add(color_id)
            sa_polygon = {
                'type': 'polygon',
                'points': polygon,
                'classId': -1 * (list(classes).index(color_id) + 1),
                'attributes': [],
                'probability': 100,
                'locked': False,
                'visible': True,
                'groupId': 0
            }
            sa_loader.append(sa_polygon)

        with open(
            os.path.join(
                sa_folder,
                filename.replace('.png', '.jpg') + "___objects.json"
            ), "w"
        ) as new_json:
            json.dump(sa_loader, new_json, indent=2)
