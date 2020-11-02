from glob import glob
import os
import cv2
import numpy as np


def _create_classes(classes):
    classes_loader = []
    for id_, name in classes.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {
            'id': id_ + 1,
            'name': name,
            'color': hexcolor,
            'attribute_groups': []
        }
        classes_loader.append(sa_classes)
    return classes_loader


def yolo_object_detection_to_sa_vector(data_path):
    classes = {}
    id_ = 0
    classes_file = open(os.path.join(data_path, 'classes.txt'))
    for line in classes_file:
        key = line.rstrip()
        if key not in classes.keys():
            classes[id_] = key
            id_ += 1

    annotations = glob(os.path.join(data_path, '*.txt'))

    sa_jsons = {}
    for annotation in annotations:
        base_name = os.path.basename(annotation)
        if base_name == 'classes.txt':
            continue

        file = open(annotation)
        file_name = os.path.splitext(base_name)[0] + '.*'
        files_list = glob(os.path.join(data_path, file_name))
        if len(files_list) == 1:
            print("'{}' image for annotation doesn't exist".format(annotation))
            continue
        elif len(files_list) > 2:
            print("'{}' multiple file for this annotation".format(annotation))
            continue
        else:
            if os.path.splitext(files_list[0])[1] == '.txt':
                file_name = files_list[1]
            else:
                file_name = files_list[0]
        img = cv2.imread(file_name)
        H, W, C = img.shape

        sa_loader = []
        for line in file:
            values = line.split()
            class_id = int(values[0])
            x_center = float(values[1]) * W
            y_center = float(values[2]) * H
            width = float(values[3]) * W
            height = float(values[4]) * H
            bbox = {
                'x1': x_center - width / 2,
                'y1': y_center - height / 2,
                'x2': x_center + width / 2,
                'y2': y_center + height / 2
            }
            sa_obj = {
                'type': 'bbox',
                'points': bbox,
                'className': classes[class_id],
                'classId': class_id + 1,
                'attributes': [],
                'probability': 100,
                'locked': False,
                'visible': True,
                'groupId': 0
            }
            sa_loader.append(sa_obj.copy())

        file_name = os.path.basename(file_name) + '___objects.json'
        sa_jsons[file_name] = sa_loader

    return sa_jsons, _create_classes(classes)