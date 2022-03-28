"""SuperAnnotate format annotation JSON helpers"""
import datetime
import json

from superannotate.lib.app.exceptions import AppException


def fill_in_missing(annotation_json, image_name: str = ""):
    for field in ["instances", "comments", "tags"]:
        if field not in annotation_json:
            annotation_json[field] = []
    if "metadata" not in annotation_json:
        annotation_json["metadata"] = {"name": image_name}


def _preprocess_annotation_json(annotation_json, image_name: str = ""):
    path = None
    if not isinstance(annotation_json, dict) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))
    elif annotation_json is None:
        annotation_json = {}

    fill_in_missing(annotation_json, image_name)

    return (annotation_json, path)


def _postprocess_annotation_json(annotation_json, path):
    if path is not None:
        json.dump(annotation_json, open(path, "w"))
        return None
    else:
        return annotation_json


def _add_created_updated(annotation):
    created_at = (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[
            :-3
        ]
        + "Z"
    )
    annotation["createdAt"] = created_at
    annotation["updatedAt"] = created_at
    return annotation


def add_annotation_comment_to_json(
    annotation_json,
    comment_text,
    comment_coords,
    comment_author,
    resolved=False,
    image_name="",
):
    """Add a comment to SuperAnnotate format annotation JSON

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: dict or Pathlike (str or Path)

    :param comment_text: comment text
    :type comment_text: str

    :param comment_coords: [x, y] coords
    :type comment_coords: list

    :param comment_author: comment author email
    :type comment_author: str

    :param resolved: comment resolve status
    :type resolved: bool
    """

    if len(comment_coords) != 2:
        raise AppException("Comment should have two values")

    annotation_json, path = _preprocess_annotation_json(
        annotation_json, image_name=image_name
    )

    user_action = {"email": comment_author, "role": "Admin"}

    annotation = {
        "x": comment_coords[0],
        "y": comment_coords[1],
        "correspondence": [{"text": comment_text, "email": comment_author}],
        "resolved": resolved,
        "createdBy": user_action,
        "updatedBy": user_action,
    }
    annotation = _add_created_updated(annotation)
    annotation_json["comments"].append(annotation)

    return _postprocess_annotation_json(annotation_json, path)


def add_annotation_bbox_to_json(
    annotation_json,
    bbox,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None,
    image_name: str = "",
):
    """Add a bounding box annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: dict or Pathlike (str or Path)

    :param bbox: 4 element list of top-left x,y and bottom-right x, y coordinates
    :type bbox: list of floats

    :param annotation_class_name: annotation class name
    :type annotation_class_name: str

    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts

    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """

    if len(bbox) != 4:
        raise AppException("Bounding boxes should have 4 float elements")

    annotation_json, path = _preprocess_annotation_json(annotation_json, image_name)

    annotation = {
        "type": "bbox",
        "points": {"x1": bbox[0], "y1": bbox[1], "x2": bbox[2], "y2": bbox[3]},
        "className": annotation_class_name,
        "error": error,
        "groupId": 0,
        "pointLabels": {},
        "locked": False,
        "visible": True,
        "attributes": []
        if annotation_class_attributes is None
        else annotation_class_attributes,
    }

    annotation = _add_created_updated(annotation)
    annotation_json["instances"].append(annotation)

    return _postprocess_annotation_json(annotation_json, path)


def add_annotation_point_to_json(
    annotation_json,
    point,
    annotation_class_name,
    image_name,
    annotation_class_attributes=None,
    error=None,
):
    """Add a point annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: dict or Pathlike (str or Path)
    :param point: [x,y] list of coordinates
    :type point: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    if len(point) != 2:
        raise AppException("Point should be 2 element float list.")

    annotation_json, path = _preprocess_annotation_json(annotation_json, image_name)

    annotation = {
        "type": "point",
        "x": point[0],
        "y": point[1],
        "className": annotation_class_name,
        "error": error,
        "groupId": 0,
        "pointLabels": {},
        "locked": False,
        "visible": True,
        "attributes": []
        if annotation_class_attributes is None
        else annotation_class_attributes,
    }

    annotation = _add_created_updated(annotation)
    annotation_json["instances"].append(annotation)

    return _postprocess_annotation_json(annotation_json, path)
