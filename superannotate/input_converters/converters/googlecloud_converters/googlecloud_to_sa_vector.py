import os
import pandas as pd
import numpy as np
import cv2


def _create_classes(classes):
    classes_loader = []
    for class_, id_ in classes.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {
            'id': id_,
            'name': class_,
            'color': hexcolor,
            'attribute_groups': []
        }
        classes_loader.append(sa_classes)
    return classes_loader


def googlecloud_object_detection_to_sa_vector(path, id_generator):
    df = pd.read_csv(path, header=None)
    dir_name = os.path.dirname(path)

    sa_jsons = {}
    classes = {}
    for idx, row in df.iterrows():
        if row[2] not in classes.keys():
            classes[row[2]] = next(id_generator)

        file_name = row[1].split('/')[-1]
        img = cv2.imread(os.path.join(dir_name, file_name))
        H, W, C = img.shape
        sa_file_name = os.path.basename(file_name) + '___objects.json'
        xmin = row[3] * W
        xmax = row[5] * W
        ymin = row[4] * H
        ymax = row[8] * H

        sa_obj = {
            'type': 'bbox',
            'points': {
                'x1': xmin,
                'y1': ymin,
                'x2': xmax,
                'y2': ymax
            },
            'className': row[2],
            'classId': classes[row[2]],
            'attributes': [],
            'probability': 100,
            'locked': False,
            'visible': True,
            'groupId': 0
        }

        if sa_file_name in sa_jsons.keys():
            sa_jsons[sa_file_name].append(sa_obj)
        else:
            sa_jsons[sa_file_name] = [sa_obj]

    return sa_jsons, _create_classes(classes)