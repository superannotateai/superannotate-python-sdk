import os
import numpy as np
import xml.etree.ElementTree as ET


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
    for class_ in set(classes):
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_class = {"name": class_, "color": hexcolor, "attribute_groups": []}
        sa_classes.append(sa_class)
    return sa_classes


def _iou(bbox1, bbox2):
    xmin1, ymin1, xmax1, ymax1 = bbox1
    xmin2, ymin2, xmax2, ymax2 = bbox2

    x = max(0, min(xmax1, xmax2) - max(xmin1, xmin2))
    y = max(0, min(ymax1, ymax2) - max(ymin1, ymin2))
    return x * y / float(
        (xmax1 - xmin1) * (ymax1 - ymin1) + (xmax2 - xmin2) *
        (ymax2 - ymin2) - x * y
    )
