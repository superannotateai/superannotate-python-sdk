from pathlib import Path

from .exceptions import SABaseException

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
