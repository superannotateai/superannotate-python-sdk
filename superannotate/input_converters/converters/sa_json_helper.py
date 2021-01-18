"""
"""


def _create_vector_instance(
    instance_type,
    points,
    pointLabels,
    attributes,
    class_name='',
    connections=[]
):
    sa_instance = {
        'type': instance_type,
        'pointLabels': pointLabels,
        'attributes': attributes,
        'creationType': 'Pre-annotation'
    }

    if instance_type == 'template':
        sa_instance['points'] = points
        sa_instance['connections'] = connections
    elif instance_type == 'point':
        sa_instance['x'] = points[0]
        sa_instance['y'] = points[1]
    elif instance_type == 'ellipse':
        sa_instance['cx'] = points[0]
        sa_instance['cy'] = points[1]
        sa_instance['rx'] = points[2]
        sa_instance['ry'] = points[3]
        sa_instance['angle'] = points[4]
    elif instance_type == 'bbox':
        sa_instance['points'] = {
            'x1': points[0],
            'y1': points[1],
            'x2': points[2],
            'y2': points[3]
        }
    elif instance_type in ('polygon', 'polyline'):
        sa_instance['points'] = points
    elif instance_type == 'cuboid':
        sa_instance['points'] = {
            'f1': {
                'x': points[0],
                'y': points[1]
            },
            'f2': {
                'x': points[2],
                'y': points[3],
            },
            'r1': {
                'x': points[4],
                'y': points[5]
            },
            'r2': {
                'x': points[6],
                'y': points[7]
            }
        }
    if class_name:
        sa_instance['className'] = class_name

    return sa_instance


def _create_pixel_instance(parts, attributes, class_name=''):
    sa_instance = {
        'attributes': attributes,
        'parts': parts,
    }
    if class_name:
        sa_instance['className'] = class_name

    return sa_instance


def _create_comment(points, comments):
    sa_comment = {
        'type': 'comment',
        'x': points[0],
        'y': points[1],
        'correspondence': comments
    }
    return sa_comment


def _create_sa_json(instances, metadata, tags=[], comments=[]):
    return {
        'instances': instances,
        'metadata': metadata,
        'tags': tags,
        'comments': comments
    }
