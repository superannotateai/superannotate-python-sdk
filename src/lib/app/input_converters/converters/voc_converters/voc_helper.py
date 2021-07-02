import os
import xml.etree.ElementTree as ET


def _get_voc_instances_from_xml(file_path):
    with open(os.path.splitext(file_path)[0] + ".xml") as f:
        tree = ET.parse(f)
    instances = tree.findall("object")
    voc_instances = []
    for instance in instances:
        class_name = instance.find("name").text
        class_attributes = []
        for attr in ["pose", "occluded", "difficult", "truncated"]:
            attr_value = instance.find(attr)
            if attr_value is not None:
                class_attributes.append({"name": attr_value.text, "groupName": attr})

        bbox = instance.find("bndbox")
        bbox = [float(bbox.find(x).text) for x in ["xmin", "ymin", "xmax", "ymax"]]
        voc_instances.append(({class_name: class_attributes}, bbox))
    return voc_instances


def _iou(bbox1, bbox2):
    xmin1, ymin1, xmax1, ymax1 = bbox1
    xmin2, ymin2, xmax2, ymax2 = bbox2

    x = max(0, min(xmax1, xmax2) - max(xmin1, xmin2))
    y = max(0, min(ymax1, ymax2) - max(ymin1, ymin2))
    return (
        x
        * y
        / float(
            (xmax1 - xmin1) * (ymax1 - ymin1)
            + (xmax2 - xmin2) * (ymax2 - ymin2)
            - x * y
        )
    )


def _get_image_shape_from_xml(file_path):
    with open(os.path.splitext(file_path)[0] + ".xml") as f:
        tree = ET.parse(f)

    size = tree.find("size")
    width = int(size.find("width").text)
    height = int(size.find("height").text)

    return height, width
