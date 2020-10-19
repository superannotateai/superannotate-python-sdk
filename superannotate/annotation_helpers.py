import json

from .exceptions import SABaseException


def add_annotation_comment_to_json(
    annotation_json,
    comment_text,
    comment_coords,
    comment_author,
    resolved=False
):
    """Add a comment to SuperAnnotate format annotation JSON


    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: list or Pathlike (str or Path)
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
        raise SABaseException(0, "Comment should have two values")

    path = None
    if not isinstance(annotation_json, list) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))

    annotation = {
        "type": "comment",
        "x": comment_coords[0],
        "y": comment_coords[1],
        "comments": [{
            "text": comment_text,
            "id": comment_author
        }],
        "resolved": resolved
    }
    if annotation_json is None:
        annotation_json = []
    annotation_json.append(annotation)

    if path is not None:
        json.dump(annotation_json, open(path, "w"))
    return annotation_json


def add_annotation_bbox_to_json(
    annotation_json,
    bbox,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a bounding box annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: list or Pathlike (str or Path)
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
        raise SABaseException(0, "Bounding boxes should have 4 float elements")

    path = None
    if not isinstance(annotation_json, list) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))

    annotation = {
        "type":
            "bbox",
        "points": {
            "x1": bbox[0],
            "y1": bbox[1],
            "x2": bbox[2],
            "y2": bbox[3]
        },
        "className":
            annotation_class_name,
        "error":
            error,
        "groupId":
            0,
        "pointLabels": {},
        "locked":
            False,
        "visible":
            True,
        "attributes":
            [] if annotation_class_attributes is None else
            annotation_class_attributes
    }
    if annotation_json is None:
        annotation_json = []
    annotation_json.append(annotation)

    if path is not None:
        json.dump(annotation_json, open(path, "w"))
    return annotation_json


def add_annotation_polygon_to_json(
    annotation_json,
    polygon,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a polygon annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: list or Pathlike (str or Path)
    :param polygon: [x1,y1,x2,y2,...] list of coordinates
    :type polygon: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    if len(polygon) % 2 != 0:
        raise SABaseException(
            0, "Polygons should be even length lists of floats."
        )

    path = None
    if not isinstance(annotation_json, list) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))

    annotation = {
        "type":
            "polygon",
        "points":
            polygon,
        "className":
            annotation_class_name,
        "error":
            error,
        "groupId":
            0,
        "pointLabels": {},
        "locked":
            False,
        "visible":
            True,
        "attributes":
            [] if annotation_class_attributes is None else
            annotation_class_attributes
    }
    if annotation_json is None:
        annotation_json = []
    annotation_json.append(annotation)

    if path is not None:
        json.dump(annotation_json, open(path, "w"))
    return annotation_json


def add_annotation_polyline_to_json(
    annotation_json,
    polyline,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a polyline annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: list or Pathlike (str or Path)
    :param polyline: [x1,y1,x2,y2,...] list of coordinates
    :type polyline: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """

    if len(polyline) % 2 != 0:
        raise SABaseException(
            0, "Polylines should be even length lists of floats."
        )

    path = None
    if not isinstance(annotation_json, list) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))

    annotation = {
        "type":
            "polyline",
        "points":
            polyline,
        "className":
            annotation_class_name,
        "error":
            error,
        "groupId":
            0,
        "pointLabels": {},
        "locked":
            False,
        "visible":
            True,
        "attributes":
            [] if annotation_class_attributes is None else
            annotation_class_attributes
    }
    if annotation_json is None:
        annotation_json = []
    annotation_json.append(annotation)

    if path is not None:
        json.dump(annotation_json, open(path, "w"))
    return annotation_json


def add_annotation_point_to_json(
    annotation_json,
    point,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a point annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: list or Pathlike (str or Path)
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
        raise SABaseException(0, "Point should be 2 element float list.")

    path = None
    if not isinstance(annotation_json, list) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))

    annotation = {
        "type":
            "point",
        "x":
            point[0],
        "y":
            point[1],
        "className":
            annotation_class_name,
        "error":
            error,
        "groupId":
            0,
        "pointLabels": {},
        "locked":
            False,
        "visible":
            True,
        "attributes":
            [] if annotation_class_attributes is None else
            annotation_class_attributes
    }
    if annotation_json is None:
        annotation_json = []
    annotation_json.append(annotation)

    if path is not None:
        json.dump(annotation_json, open(path, "w"))
    return annotation_json


def add_annotation_ellipse_to_json(
    annotation_json,
    ellipse,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add an ellipse annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: list or Pathlike (str or Path)
    :param ellipse: [center_x, center_y, r_x, r_y, angle]
                    list of coordinates and rotation angle in degrees around y
                    axis
    :type ellipse: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    if len(ellipse) != 5:
        raise SABaseException(0, "Ellipse should be 5 element float list.")

    path = None
    if not isinstance(annotation_json, list) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))

    annotation = {
        "type":
            "ellipse",
        "cx":
            ellipse[0],
        "cy":
            ellipse[1],
        "rx":
            ellipse[2],
        "ry":
            ellipse[3],
        "angle":
            ellipse[4],
        "className":
            annotation_class_name,
        "error":
            error,
        "groupId":
            0,
        "pointLabels": {},
        "locked":
            False,
        "visible":
            True,
        "attributes":
            [] if annotation_class_attributes is None else
            annotation_class_attributes
    }
    if annotation_json is None:
        annotation_json = []
    annotation_json.append(annotation)

    if path is not None:
        json.dump(annotation_json, open(path, "w"))
    return annotation_json


def add_annotation_template_to_json(
    annotation_json,
    template_points,
    template_connections,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a template annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: list or Pathlike (str or Path)
    :param template_points: [x1,y1,x2,y2,...] list of coordinates
    :type template_points: list of floats
    :param template_connections: [from_id_1,to_id_1,from_id_2,to_id_2,...]
                                 list of indexes from -> to. Indexes are based
                                 on template_points. E.g., to have x1,y1 to connect
                                 to x2,y2 and x1,y1 to connect to x4,y4,
                                 need: [1,2,1,4,...]
    :type template_connections: list of ints
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    if len(template_points) % 2 != 0:
        raise SABaseException(
            0, "template_points should be even length lists of floats."
        )
    if len(template_connections) % 2 != 0:
        raise SABaseException(
            0, "template_connections should be even length lists of ints."
        )

    path = None
    if not isinstance(annotation_json, list) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))

    annotation = {
        "type":
            "template",
        "points": [],
        "connections": [],
        "className":
            annotation_class_name,
        "error":
            error,
        "groupId":
            0,
        "pointLabels": {},
        "locked":
            False,
        "visible":
            True,
        "attributes":
            [] if annotation_class_attributes is None else
            annotation_class_attributes
    }
    for i in range(0, len(template_points), 2):
        annotation["points"].append(
            {
                "id": i // 2 + 1,
                "x": template_points[i],
                "y": template_points[i + 1]
            }
        )
    for i in range(0, len(template_connections), 2):
        annotation["connections"].append(
            {
                "id": i // 2 + 1,
                "from": template_connections[i],
                "to": template_connections[i + 1]
            }
        )
    if annotation_json is None:
        annotation_json = []
    annotation_json.append(annotation)

    if path is not None:
        json.dump(annotation_json, open(path, "w"))
    return annotation_json


def add_annotation_cuboid_to_json(
    annotation_json,
    cuboid,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a cuboid annotation to SuperAnnotate format annotation JSON

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param annotation_json: annotations in SuperAnnotate format JSON or filepath to JSON
    :type annotation_json: list or Pathlike (str or Path)
    :param cuboid: [x_front_tl,y_front_tl,x_front_br,y_front_br,
                    x_rear_tl,y_rear_tl,x_rear_br,y_rear_br] list of coordinates
                    of front rectangle and back rectangle, in top-left (tl) and
                    bottom-right (br) format
    :type cuboid: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of attributes
    :type error: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    if len(cuboid) != 8:
        raise SABaseException(0, "cuboid should be lenght 8 list of floats.")

    path = None
    if not isinstance(annotation_json, list) and annotation_json is not None:
        path = annotation_json
        annotation_json = json.load(open(annotation_json))

    annotation = {
        "type":
            "cuboid",
        "points":
            {
                "f1": {
                    "x": cuboid[0],
                    "y": cuboid[1]
                },
                "f2": {
                    "x": cuboid[2],
                    "y": cuboid[3]
                },
                "r1": {
                    "x": cuboid[4],
                    "y": cuboid[5]
                },
                "r2": {
                    "x": cuboid[6],
                    "y": cuboid[7]
                },
            },
        "className":
            annotation_class_name,
        "error":
            error,
        "groupId":
            0,
        "pointLabels": {},
        "locked":
            False,
        "visible":
            True,
        "attributes":
            [] if annotation_class_attributes is None else
            annotation_class_attributes
    }
    if annotation_json is None:
        annotation_json = []
    annotation_json.append(annotation)

    if path is not None:
        json.dump(annotation_json, open(path, "w"))
    return annotation_json
