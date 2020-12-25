import json
import numpy as np

from pathlib import Path

from .dataloop_helper import (_update_classes_dict, _create_attributes_list)

from ..sa_json_helper import _create_vector_instance, _create_comment

from ....common import write_to_json


def dataloop_to_sa(input_dir, task, output_dir):
    classes = {}
    json_data = Path(input_dir).glob('*.json')
    if task == 'object_detection':
        instance_types = ['box']
    elif task == 'instance_segmentation':
        instance_types = ['segment']
    elif task == 'vector_annotation':
        instance_types = ['point', 'box', 'ellipse', 'segment']

    tags_type = 'class'
    comment_type = 'note'

    for json_file in json_data:
        sa_loader = []
        dl_data = json.load(open(json_file))

        for ann in dl_data['annotations']:
            if ann['type'] in instance_types:
                classes = _update_classes_dict(
                    classes, ann['label'], ann['attributes']
                )

            attributes = _create_attributes_list(ann['attributes'])

            if ann['type'] in instance_types:
                if ann['type'] == 'segment' and len(ann['coordinates']) == 1:
                    points = []
                    for sub_list in ann['coordinates']:
                        for sub_dict in sub_list:
                            points.append(sub_dict['x'])
                            points.append(sub_dict['y'])
                    instance_type = 'polygon'
                elif ann['type'] == 'box':
                    points = (
                        ann['coordinates'][0]['x'], ann['coordinates'][0]['y'],
                        ann['coordinates'][1]['x'], ann['coordinates'][1]['y']
                    )
                    instance_type = 'bbox'
                elif ann['type'] == 'ellipse':
                    points = (
                        ann['coordinates']['center']['x'],
                        ann['coordinates']['center']['y'],
                        ann['coordinates']['rx'], ann['coordinates']['ry'],
                        ann['coordinates']['angle']
                    )
                    instance_type = 'ellipse'
                elif ann['type'] == 'point':
                    points = (ann['coordinates']['x'], ann['coordinates']['y'])
                    instance_type = 'point'
                sa_obj = _create_vector_instance(
                    instance_type, points, {}, attributes, ann['label']
                )
                sa_loader.append(sa_obj)
            elif ann['type'] == comment_type:
                comments = []
                for note in ann['coordinates']['note']['messages']:
                    comments.append(
                        {
                            'text': note['body'],
                            'id': note['creator']
                        }
                    )
                    points = (
                        ann['coordinates']['box'][0]['x'],
                        ann['coordinates']['box'][0]['y']
                    )
                    sa_comment = _create_comment(points, comments)
                sa_loader.append(sa_comment)
            elif ann['type'] == tags_type:
                sa_tags = {'type': 'tag', 'name': ann['label']}
                sa_loader.append(sa_tags)

        file_name = '%s___objects.json' % dl_data['filename'][1:]
        write_to_json(output_dir / file_name, sa_loader)
    return classes
