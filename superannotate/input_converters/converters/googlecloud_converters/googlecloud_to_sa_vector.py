import os
import pandas as pd
import numpy as np
import cv2

from ..sa_json_helper import _create_vector_instance


def _create_classes(classes):
    classes_loader = []
    for class_ in set(classes):
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {'name': class_, 'color': hexcolor, 'attribute_groups': []}
        classes_loader.append(sa_classes)
    return classes_loader


def googlecloud_to_sa_vector(path):
    df = pd.read_csv(path, header=None)
    dir_name = path.parent

    sa_jsons = {}
    classes = []
    for _, row in df.iterrows():
        classes.append(row[2])

        file_name = row[1].split('/')[-1]
        img = cv2.imread(str(dir_name / file_name))
        H, W, _ = img.shape
        sa_file_name = '%s___objects.json' % os.path.basename(file_name)

        points = (row[3] * W, row[4] * H, row[5] * W, row[8] * H)
        sa_obj = _create_vector_instance('bbox', points, {}, [], row[2])

        if sa_file_name in sa_jsons.keys():
            sa_jsons[sa_file_name].append(sa_obj)
        else:
            sa_jsons[sa_file_name] = [sa_obj]

    return sa_jsons, _create_classes(classes)
