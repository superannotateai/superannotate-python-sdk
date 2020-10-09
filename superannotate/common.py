import numpy as np
import functools
import logging
from pathlib import Path

from .exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")

_PROJECT_TYPES = {"Vector": 1, "Pixel": 2}
_ANNOTATION_STATUSES = {
    "NotStarted": 1,
    "InProgress": 2,
    "QualityCheck": 3,
    "Returned": 4,
    "Completed": 5,
    "Skipped": 6
}
_USER_ROLES = {"Admin": 2, "Annotator": 3, "QA": 4, "Customer": 5, "Viewer": 6}


def image_path_to_annotation_paths(image_path, project_type):
    image_path = Path(image_path)
    project_type = project_type_str_to_int(project_type)
    postfix_json = '___objects.json' if project_type == 1 else '___pixel.json'
    postfix_mask = '___save.png'
    if project_type == 1:
        return (image_path.parent / (image_path.name + postfix_json), )
    else:
        return (
            image_path.parent / (image_path.name + postfix_json),
            image_path.parent / (image_path.name + postfix_mask)
        )


def project_type_str_to_int(project_type):
    if project_type not in _PROJECT_TYPES:
        raise SABaseException(
            0, "Project type should be one of Vector or Pixel ."
        )
    return _PROJECT_TYPES[project_type]


def project_type_int_to_str(project_type):
    """Converts metadata project_type int value to a string

    :param project_type: int in project metadata's 'type' key
    :type project_type: int

    :return: 'Vector' or 'Pixel'
    :rtype: str
    """

    for k, v in _PROJECT_TYPES.items():
        if v == project_type:
            return k
    raise SABaseException(0, "Project type should be one of 1 or 2 .")


def user_role_str_to_int(user_role):
    if user_role not in _USER_ROLES:
        raise SABaseException(
            0,
            "User role should be one of Admin , Annotator , QA , Customer , Viewer ."
        )
    return _USER_ROLES[user_role]


def user_role_int_to_str(user_role):
    for k, v in _USER_ROLES.items():
        if v == user_role:
            return k
    raise SABaseException(0, "User role should be one of 2 3 4 5 6 .")


def annotation_status_str_to_int(annotation_status):
    if annotation_status not in _ANNOTATION_STATUSES:
        raise SABaseException(
            0,
            "Annotation status should be one of NotStarted InProgress QualityCheck Returned Completed Skipped"
        )
    return _ANNOTATION_STATUSES[annotation_status]


def annotation_status_int_to_str(annotation_status):
    """Converts metadata annotation_status int value to a string

    :param annotation_status: int in image metadata's 'annotation_status' key
    :type annotation_status: int

    :return: One of 'NotStarted' 'InProgress' 'QualityCheck' 'Returned' 'Completed' 'Skipped'
    :rtype: str
    """

    for k, v in _ANNOTATION_STATUSES.items():
        if v == annotation_status:
            return k
    raise SABaseException(
        0, "Annotation status should be one of 1, 2, 3, 4, 5, 6 ."
    )


def deprecated_alias(**aliases):
    def deco(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            rename_kwargs(f.__name__, kwargs, aliases)
            return f(*args, **kwargs)

        return wrapper

    return deco


def rename_kwargs(func_name, kwargs, aliases):
    for alias, new in aliases.items():
        if alias in kwargs:
            if new in kwargs:
                raise TypeError(
                    '{} received both {} and {}'.format(func_name, alias, new)
                )
            logger.warning(
                '%s is deprecated; use %s in %s', alias, new, func_name
            )
            kwargs[new] = kwargs.pop(alias)


logger = logging.getLogger('httplogger')


def hex_to_rgb(hex_string):
    """Converts HEX values to RGB values
    """
    h = hex_string.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb_tuple):
    """Converts RGB values to HEX values
    """
    return '#%02x%02x%02x' % rgb_tuple


def blue_color_generator(n, hex_values=True):
    """ Blue colors generator for SuperAnnotate blue mask.
    """
    hex_colors = []
    for i in range(n + 1):
        int_color = i * 15
        bgr_color = np.array(
            [
                int_color & 255, (int_color >> 8) & 255,
                (int_color >> 16) & 255, 255
            ],
            dtype=np.uint8
        )
        hex_color = '#' + "{:02x}".format(
            bgr_color[2]
        ) + "{:02x}".format(bgr_color[1], ) + "{:02x}".format(bgr_color[0])
        if hex_values:
            hex_colors.append(hex_color)
        else:
            hex_colors.append(hex_to_rgb(hex_color))
    return hex_colors[1:]
