import os
import json
import numpy as np
import xml.etree.ElementTree as ET
from tqdm import tqdm


def voc_object_detection_to_sa_vector(voc_root, sa_root):
    classes = set()
    annotation_dirname = os.path.join(os.path.join(voc_root, "Annotations/"))
    annotation_files = np.array(os.listdir(annotation_dirname))
    for filename in tqdm(annotation_files):
        anno_file = os.path.join(annotation_dirname, filename)
        with open(anno_file) as f:
            tree = ET.parse(f)
        sa_base_element = {
            'type': "bbox",
            'classId': None,
            'className': None,
            'probability': 100,
            'points': [],
            'attributes': [],
            'attributeNames': []
        }
        sa_loader = []
        instances = tree.findall("object")
        for instance in instances:
            class_name = instance.find("name").text
            classes.add(class_name)
            bbox = instance.find("bndbox")
            bbox = [
                float(bbox.find(x).text)
                for x in ["xmin", "ymin", "xmax", "ymax"]
            ]
            instance = dict(sa_base_element)
            instance["classId"] = list(classes).index(class_name)
            instance["className"] = class_name
            instance["points"] = {
                "x1": bbox[0],
                "x2": bbox[2],
                "y1": bbox[1],
                "y2": bbox[3]
            }
            sa_loader.append(instance)
        image_id = filename.split(".")[0]
        annpath = os.path.join(
            sa_root, "{}.jpg___objects.json".format(image_id)
        )
        with open(annpath, "w") as fp:
            json.dump(sa_loader, fp, indent=2)

    #generate classes json
    sa_classes = []
    for idx, class_name in enumerate(classes):
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_class = {
            "id": idx,
            "name": class_name,
            "color": hexcolor,
            "attribute_groups": []
        }
        sa_classes.append(sa_class)

    with open(
        os.path.join(sa_root, "classes", "classes.json"), "w+"
    ) as classes_json:
        classes_json.write(json.dumps(sa_classes, indent=2))