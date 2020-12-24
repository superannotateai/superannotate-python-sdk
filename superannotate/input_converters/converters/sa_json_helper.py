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
    else:
        sa_instance['points'] = points

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


def _create_comment():
    pass


def _create_empty_sa_json():
    return {'metadata': {}, 'instances': [], 'tags': [], 'comments': []}