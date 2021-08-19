import base64
import zlib

import cv2
import numpy as np


def _base64_to_polygon(bitmap):
    z = zlib.decompress(base64.b64decode(bitmap))
    n = np.frombuffer(z, np.uint8)
    mask = cv2.imdecode(n, cv2.IMREAD_UNCHANGED)[:, :, 3].astype(bool)
    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    segmentation = []

    for contour in contours:
        contour = contour.flatten().tolist()
        if len(contour) > 4:
            segmentation.append(contour)
        if len(segmentation) == 0:
            continue
    return segmentation


def _create_attribute_list(sv_attributes, class_name, class_id_map):
    attributes = []
    for tag in sv_attributes:
        group_name = class_id_map[class_name]["attr_group"]["group_name"]
        attr_name = tag["name"]
        attributes.append({"name": attr_name, "groupName": group_name})
    return attributes
