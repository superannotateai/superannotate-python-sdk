from pathlib import Path

import cv2
import pandas as pd

from ..sa_json_helper import (_create_vector_instance, _create_sa_json)

from ....common import write_to_json


def googlecloud_to_sa_vector(path, output_dir):
    df = pd.read_csv(path, header=None)
    dir_name = path.parent

    sa_jsons = {}
    classes = []
    for _, row in df.iterrows():
        classes.append(row[2])

        file_name = row[1].split('/')[-1]
        img = cv2.imread(str(dir_name / file_name))
        H, W, _ = img.shape
        sa_file_name = '%s___objects.json' % Path(file_name).name

        points = (row[3] * W, row[4] * H, row[5] * W, row[8] * H)
        sa_instances = _create_vector_instance('bbox', points, {}, [], row[2])

        if sa_file_name in sa_jsons.keys():
            sa_jsons[sa_file_name]['instances'].append(sa_instances)
        else:
            sa_metadata = {
                'name': Path(file_name).name,
                'width': W,
                'height': H
            }
            sa_jsons[sa_file_name] = {
                'metadata': sa_metadata,
                'instances': [sa_instances]
            }

    for key, value in sa_jsons.items():
        sa_json = _create_sa_json(value['instances'], value['metadata'])
        write_to_json(output_dir / key, sa_json)

    return classes
