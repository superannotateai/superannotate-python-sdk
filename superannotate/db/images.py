import io
import json
import logging
from pathlib import Path

import boto3
import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw

from ..annotation_helpers import (
    add_annotation_bbox_to_json, add_annotation_comment_to_json,
    add_annotation_cuboid_to_json, add_annotation_ellipse_to_json,
    add_annotation_point_to_json, add_annotation_polygon_to_json,
    add_annotation_polyline_to_json, add_annotation_template_to_json
)
from ..api import API
from ..common import (
    annotation_status_str_to_int, deprecated_alias, hex_to_rgb,
    image_path_to_annotation_paths, project_type_int_to_str
)
from ..exceptions import SABaseException
from .annotation_classes import (
    fill_class_and_attribute_ids, fill_class_and_attribute_names,
    get_annotation_classes_id_to_name, get_annotation_classes_name_to_id,
    search_annotation_classes
)
from .project import get_project_metadata

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()


def _get_project_root_folder_id(project):
    """Get root folder ID
    Returns
    -------
    int
        Root folder ID
    """
    params = {'team_id': project['team_id']}
    response = _api.send_request(
        req_type='GET', path=f'/project/{project["id"]}', params=params
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    return response.json()['folder_id']


def search_images(
    project,
    image_name_prefix=None,
    annotation_status=None,
    return_metadata=False
):
    """Search images by name_prefix (case-insensitive) and annotation status

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name_prefix: image name prefix for search
    :type image_name_prefix: str
    :param annotation_status: if not None, annotation statuses of images to filter,
                              should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :param return_metadata: return metadata of images instead of names
    :type return_metadata: bool

    :return: metadata of found images or image names
    :rtype: list of dicts or strs
    """
    if not isinstance(project, dict):
        project = get_project_metadata(project)
    team_id, project_id = project["team_id"], project["id"]
    folder_id = _get_project_root_folder_id(project)  # maybe changed in future
    if annotation_status is not None:
        annotation_status = annotation_status_str_to_int(annotation_status)

    result_list = []
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'folder_id': folder_id,
        'annotation_status': annotation_status,
        'offset': 0
    }
    if image_name_prefix is not None:
        params['name'] = image_name_prefix
    total_got = 0
    while True:
        response = _api.send_request(
            req_type='GET', path='/images', params=params
        )
        if response.ok:
            # print(response.json())
            results = response.json()["data"]
            total_got += len(results)
            for r in results:
                if return_metadata:
                    result_list.append(r)
                else:
                    result_list.append(r["name"])
            if response.json()["count"] <= total_got:
                break
            params["offset"] = total_got
            # print(
            #     "Got to ", len(result_list),
            #     response.json()["count"], len(new_results), params['offset']
            # )
        else:
            raise SABaseException(
                response.status_code, "Couldn't search images " + response.text
            )
    return result_list


def get_image_metadata(project, image_name):
    """Returns image metadata

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str

    :return: metadata of image
    :rtype: dict
    """
    images = search_images(project, image_name, return_metadata=True)
    for image in images:
        if image["name"] == image_name:
            return image
    raise SABaseException(
        0, "Image " + image_name + " doesn't exist in the project " +
        project["name"]
    )


def set_image_annotation_status(project, image_name, annotation_status):
    """Sets the image annotation status

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param annotation_status: annotation status to set,
           should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :return: metadata of the updated image
    :rtype: dict
    """
    image = get_image_metadata(project, image_name)
    team_id, project_id, image_id = image["team_id"], image["project_id"
                                                           ], image["id"]
    annotation_status = annotation_status_str_to_int(annotation_status)
    json_req = {
        "annotation_status": annotation_status,
    }
    params = {'team_id': team_id, 'project_id': project_id}
    response = _api.send_request(
        req_type='PUT',
        path=f'/image/{image_id}',
        json_req=json_req,
        params=params
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    return response.json()


def add_annotation_comment_to_image(
    project,
    image_name,
    comment_text,
    comment_coords,
    comment_author,
    resolved=False
):
    """Add a comment to SuperAnnotate format annotation JSON

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param comment_text: comment text
    :type comment_text: str
    :param comment_coords: [x, y] coords
    :type comment_coords: list
    :param comment_author: comment author email
    :type comment_author: str
    :param resolved: comment resolve status
    :type resolved: bool
    """
    annotations = get_image_annotations(project, image_name)["annotation_json"]
    annotations = add_annotation_comment_to_json(
        annotations,
        comment_text,
        comment_coords,
        comment_author,
        resolved=resolved
    )
    upload_annotations_from_json_to_image(
        project, image_name, annotations, verbose=False
    )


def add_annotation_bbox_to_image(
    project,
    image_name,
    bbox,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None,
):
    """Add a bounding box annotation to image annotations

    annotation_class_attributes has the form [ {"name" : "<attribute_value>" }, "groupName" : "<attribute_group>"} ], ... ]

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param bbox: 4 element list of top-left x,y and bottom-right x, y coordinates
    :type bbox: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    annotations = get_image_annotations(project, image_name)["annotation_json"]
    annotations = add_annotation_bbox_to_json(
        annotations,
        bbox,
        annotation_class_name,
        annotation_class_attributes,
        error,
    )
    upload_annotations_from_json_to_image(
        project, image_name, annotations, verbose=False
    )


def add_annotation_polygon_to_image(
    project,
    image_name,
    polygon,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a polygon annotation to image annotations

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param polygon: [x1,y1,x2,y2,...] list of coordinates
    :type polygon: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """

    annotations = get_image_annotations(project, image_name)["annotation_json"]
    annotations = add_annotation_polygon_to_json(
        annotations, polygon, annotation_class_name,
        annotation_class_attributes, error
    )
    upload_annotations_from_json_to_image(
        project, image_name, annotations, verbose=False
    )


def add_annotation_polyline_to_image(
    project,
    image_name,
    polyline,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a polyline annotation to image annotations

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param polyline: [x1,y1,x2,y2,...] list of coordinates
    :type polyline: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    annotations = get_image_annotations(project, image_name)["annotation_json"]
    annotations = add_annotation_polyline_to_json(
        annotations, polyline, annotation_class_name,
        annotation_class_attributes, error
    )
    upload_annotations_from_json_to_image(
        project, image_name, annotations, verbose=False
    )


def add_annotation_point_to_image(
    project,
    image_name,
    point,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a point annotation to image annotations

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param point: [x,y] list of coordinates
    :type point: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    annotations = get_image_annotations(project, image_name)["annotation_json"]
    annotations = add_annotation_point_to_json(
        annotations, point, annotation_class_name, annotation_class_attributes,
        error
    )
    upload_annotations_from_json_to_image(
        project, image_name, annotations, verbose=False
    )


def add_annotation_ellipse_to_image(
    project,
    image_name,
    ellipse,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add an ellipse annotation to image annotations

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param ellipse: [center_x, center_y, r_x, r_y, angle] list of coordinates and angle
    :type ellipse: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    annotations = get_image_annotations(project, image_name)["annotation_json"]
    annotations = add_annotation_ellipse_to_json(
        annotations, ellipse, annotation_class_name,
        annotation_class_attributes, error
    )
    upload_annotations_from_json_to_image(
        project, image_name, annotations, verbose=False
    )


def add_annotation_template_to_image(
    project,
    image_name,
    template_points,
    template_connections,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a template annotation to image annotations

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
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
    annotations = get_image_annotations(project, image_name)["annotation_json"]
    annotations = add_annotation_template_to_json(
        annotations, template_points, template_connections,
        annotation_class_name, annotation_class_attributes, error
    )
    upload_annotations_from_json_to_image(
        project, image_name, annotations, verbose=False
    )


def add_annotation_cuboid_to_image(
    project,
    image_name,
    cuboid,
    annotation_class_name,
    annotation_class_attributes=None,
    error=None
):
    """Add a cuboid annotation to image annotations

    annotation_class_attributes has the form [ {"name" : "<attribute_value>", "groupName" : "<attribute_group>"},  ... ]

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param cuboid: [x_front_tl,y_front_tl,x_front_br,y_front_br,
                    x_back_tl,y_back_tl,x_back_br,y_back_br] list of coordinates
                    of front rectangle and back rectangle, in top-left and
                    bottom-right format
    :type cuboid: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param annotation_class_attributes: list of annotation class attributes
    :type annotation_class_attributes: list of 2 element dicts
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    annotations = get_image_annotations(project, image_name)["annotation_json"]
    annotations = add_annotation_cuboid_to_json(
        annotations, cuboid, annotation_class_name, annotation_class_attributes,
        error
    )
    upload_annotations_from_json_to_image(
        project, image_name, annotations, verbose=False
    )


def download_image(
    project,
    image_name,
    local_dir_path=".",
    include_annotations=False,
    include_fuse=False,
    include_overlay=False,
    variant='original'
):
    """Downloads the image (and annotation if not None) to local_dir_path

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param local_dir_path: where to download the image
    :type local_dir_path: Pathlike (str or Path)
    :param include_annotations: enables annotation download with the image
    :type include_annotations: bool
    :param include_fuse: enables fuse image download with the image
    :type include_fuse: bool
    :param variant: which resolution to download, can be 'original' or 'lores'
     (low resolution used in web editor)
    :type variant: str

    :return: paths of downloaded image and annotations if included
    :rtype: tuple
    """
    if not Path(local_dir_path).is_dir():
        raise SABaseException(
            0, f"local_dir_path {local_dir_path} is not an existing directory"
        )
    if variant not in ["original", "lores"]:
        raise SABaseException(
            0, "Image download variant should be either original or lores"
        )

    if not isinstance(project, dict):
        project = get_project_metadata(project)
    img = get_image_bytes(project, image_name, variant=variant)
    if variant == "lores":
        image_name += "___lores.jpg"
    filepath = Path(local_dir_path) / image_name
    with open(filepath, 'wb') as f:
        f.write(img.getbuffer())
    annotations_filepaths = None
    fuse_path = None
    if include_annotations:
        annotations_filepaths = download_image_annotations(
            project, image_name, local_dir_path
        )
        if include_fuse or include_overlay:
            classes = search_annotation_classes(project, return_metadata=True)
            project_type = project_type_int_to_str(project["type"])
            fuse_path = create_fuse_image(
                filepath, classes, project_type, output_overlay=include_overlay
            )
    logger.info("Downloaded image %s to %s.", image_name, filepath)

    return (str(filepath), annotations_filepaths, fuse_path)


def delete_image(project, image_name):
    """Deletes image

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    """
    image = get_image_metadata(project, image_name)
    team_id, project_id, image_id = image["team_id"], image["project_id"
                                                           ], image["id"]
    params = {"team_id": team_id, "project_id": project_id}
    response = _api.send_request(
        req_type='DELETE', path=f'/image/{image_id}', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't delete image " + response.text
        )
    logger.info("Successfully deleted image  %s.", image_name)


def get_image_bytes(project, image_name, variant='original'):
    """Returns an io.BytesIO() object of the image. Suitable for creating
    PIL.Image out of it.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param variant: which resolution to get, can be 'original' or 'lores'
     (low resolution)
    :type variant: str

    :return: io.BytesIO() of the image
    :rtype: io.BytesIO()
    """
    if variant not in ["original", "lores"]:
        raise SABaseException(
            0, "Image download variant should be either original or lores"
        )
    image = get_image_metadata(project, image_name)
    team_id, project_id, image_id, folder_id = image["team_id"], image[
        "project_id"], image["id"], image['folder_id']
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'folder_id': folder_id,
        'include_original': 1
    }
    response = _api.send_request(
        req_type='GET',
        path=f'/image/{image_id}/annotation/getAnnotationDownloadToken',
        params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get image " + response.text
        )
    res = response.json()
    url = res[variant]["url"]
    headers = res[variant]["headers"]
    response = requests.get(url=url, headers=headers)
    img = io.BytesIO(response.content)
    return img


def get_image_preannotations(project, image_name):
    """Get pre-annotations of the image. Only works for "vector" projects.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str

    :return: dict object with following keys:
        "preannotation_json": dict object of the annotation,
        "preannotation_json_filename": filename on server,
    :rtype: dict
    """
    image = get_image_metadata(project, image_name)
    team_id, project_id, image_id, folder_id = image["team_id"], image[
        "project_id"], image["id"], image['folder_id']
    if not isinstance(project, dict):
        project = get_project_metadata(project)
    project_type = project["type"]

    params = {
        'team_id': team_id,
        'project_id': project_id,
        'folder_id': folder_id
    }
    response = _api.send_request(
        req_type='GET',
        path=f'/image/{image_id}/annotation/getAnnotationDownloadToken',
        params=params
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    res = response.json()

    annotation_classes = search_annotation_classes(
        project, return_metadata=True
    )
    annotation_classes_dict = get_annotation_classes_id_to_name(
        annotation_classes
    )
    if project_type == 1:  # vector
        res = res['preannotation']
        url = res["url"]
        annotation_json_filename = url.rsplit('/', 1)[-1]
        headers = res["headers"]
        response = requests.get(url=url, headers=headers)
        if not response.ok:
            logger.warning(
                "No preannotation available for image %s.", image_name
            )
            return {
                "preannotation_json_filename": None,
                "preannotation_json": None
            }
        res_json = response.json()
        fill_class_and_attribute_names(res_json, annotation_classes_dict)
        return {
            "preannotation_json_filename": annotation_json_filename,
            "preannotation_json": res_json
        }
    else:  # pixel
        res_json = res['preAnnotationJson']
        url = res_json["url"]
        preannotation_json_filename = url.rsplit('/', 1)[-1]
        headers = res_json["headers"]
        response = requests.get(url=url, headers=headers)
        if not response.ok:
            logger.warning("No preannotation available.")
            return {
                "preannotation_json_filename": None,
                "preannotation_json": None,
                "preannotation_mask_filename": None,
                "preannotation_mask": None,
            }
        preannotation_json = response.json()
        fill_class_and_attribute_names(
            preannotation_json, annotation_classes_dict
        )

        res_mask = res['preAnnotationSavePng']
        url = res_mask["url"]
        preannotation_mask_filename = url.rsplit('/', 1)[-1]
        annotation_json_filename = url.rsplit('/', 1)[-1]
        headers = res_mask["headers"]
        response = requests.get(url=url, headers=headers)
        mask = io.BytesIO(response.content)
        return {
            "preannotation_json_filename": preannotation_json_filename,
            "preannotation_json": preannotation_json,
            "preannotation_mask_filename": preannotation_mask_filename,
            "preannotation_mask": mask
        }


def get_image_annotations(project, image_name, project_type=None):
    """Get annotations of the image.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str

    :return: dict object with following keys:
        "annotation_json": dict object of the annotation,
        "annotation_json_filename": filename on server,
        "annotation_mask": mask (for pixel),
        "annotation_mask_filename": mask filename on server
    :rtype: dict
    """
    image = get_image_metadata(project, image_name)
    team_id, project_id, image_id, folder_id = image["team_id"], image[
        "project_id"], image["id"], image['folder_id']
    if project_type is None:
        if not isinstance(project, dict):
            project = get_project_metadata(project)
        project_type = project["type"]
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'folder_id': folder_id
    }
    response = _api.send_request(
        req_type='GET',
        path=f'/image/{image_id}/annotation/getAnnotationDownloadToken',
        params=params
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    res = response.json()

    annotation_classes = search_annotation_classes(
        project, return_metadata=True
    )
    annotation_classes_dict = get_annotation_classes_id_to_name(
        annotation_classes
    )
    if project_type == 1:  # vector
        url = res["objects"]["url"]
        annotation_json_filename = url.rsplit('/', 1)[-1]
        headers = res["objects"]["headers"]
        response = requests.get(url=url, headers=headers)
        if response.ok:
            res_json = response.json()
            fill_class_and_attribute_names(res_json, annotation_classes_dict)
            return {
                "annotation_json_filename": annotation_json_filename,
                "annotation_json": res_json
            }
        if not response.ok and response.status_code == 403:
            return {"annotation_json": None, "annotation_json_filename": None}
        raise SABaseException(response.status_code, response.text)
    else:  # pixel
        url = res["pixelObjects"]["url"]
        annotation_json_filename = url.rsplit('/', 1)[-1]
        headers = res["pixelObjects"]["headers"]
        response = requests.get(url=url, headers=headers)
        if not response.ok and response.status_code == 403:
            return {
                "annotation_json": None,
                "annotation_json_filename": None,
                "annotation_mask": None,
                "annotation_mask_filename": None
            }
        elif not response.ok:
            raise SABaseException(response.status_code, response.text)
        res_json = response.json()
        fill_class_and_attribute_names(res_json, annotation_classes_dict)
        url = res["pixelSave"]["url"]
        annotation_mask_filename = url.rsplit('/', 1)[-1]
        headers = res["pixelSave"]["headers"]
        response = requests.get(url=url, headers=headers)
        if not response.ok:
            raise SABaseException(response.status_code, response.text)
        mask = io.BytesIO(response.content)
        return {
            "annotation_json": res_json,
            "annotation_json_filename": annotation_json_filename,
            "annotation_mask": mask,
            "annotation_mask_filename": annotation_mask_filename
        }


def download_image_annotations(project, image_name, local_dir_path):
    """Downloads annotations of the image (JSON and mask if pixel type project)
    to local_dir_path.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param local_dir_path: local directory path to download to
    :type local_dir_path: Pathlike (str or Path)

    :return: paths of downloaded annotations
    :rtype: tuple
    """
    if not isinstance(project, dict):
        project = get_project_metadata(project)

    annotation = get_image_annotations(project, image_name)

    if annotation["annotation_json_filename"] is None:
        image = get_image_metadata(project, image_name)
        logger.info("No annotation found for image %s.", image["name"])
        return None
    return_filepaths = []
    json_path = Path(local_dir_path) / annotation["annotation_json_filename"]
    return_filepaths.append(str(json_path))
    if project["type"] == 1:
        with open(json_path, "w") as f:
            json.dump(annotation["annotation_json"], f, indent=4)
    else:
        with open(json_path, "w") as f:
            json.dump(annotation["annotation_json"], f, indent=4)
        mask_path = Path(local_dir_path
                        ) / annotation["annotation_mask_filename"]
        return_filepaths.append(str(mask_path))
        with open(mask_path, "wb") as f:
            f.write(annotation["annotation_mask"].getbuffer())

    return tuple(return_filepaths)


def download_image_preannotations(project, image_name, local_dir_path):
    """Downloads pre-annotations of the image to local_dir_path.
    Only works for "vector" projects.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param local_dir_path: local directory path to download to
    :type local_dir_path: Pathlike (str or Path)

    :return: paths of downloaded pre-annotations
    :rtype: tuple
    """
    if not isinstance(project, dict):
        project = get_project_metadata(project)
    annotation = get_image_preannotations(project, image_name)
    if annotation["preannotation_json_filename"] is None:
        return (None, )
    return_filepaths = []
    json_path = Path(local_dir_path) / annotation["preannotation_json_filename"]
    return_filepaths.append(str(json_path))
    if project["type"] == 1:
        with open(json_path, "w") as f:
            json.dump(annotation["preannotation_json"], f)
    else:
        with open(json_path, "w") as f:
            json.dump(annotation["preannotation_json"], f)
        mask_path = Path(local_dir_path
                        ) / annotation["preannotation_mask_filename"]
        with open(mask_path, "wb") as f:
            f.write(annotation["preannotation_mask"].getbuffer())
        return_filepaths.append(str(mask_path))
    return tuple(return_filepaths)


@deprecated_alias(mask_path="mask")
def upload_annotations_from_json_to_image(
    project, image_name, annotation_json, mask=None, verbose=True
):
    """Upload annotations from JSON (also mask for pixel annotations)
    to the image.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param annotation_json: annotations in SuperAnnotate format JSON dict or path to JSON file
    :type annotation_json: dict or Pathlike (str or Path)
    :param mask: BytesIO object or filepath to mask annotation for pixel projects in SuperAnnotate format
    :type mask: BytesIO or Pathlike (str or Path)
    """

    if not isinstance(annotation_json, list):
        if verbose:
            logger.info("Uploading annotations from %s.", annotation_json)
        annotation_json = json.load(open(annotation_json))
    if not isinstance(project, dict):
        project = get_project_metadata(project)
    image = get_image_metadata(project, image_name)
    team_id, project_id, image_id, folder_id, image_name = image[
        "team_id"], image["project_id"], image["id"], image['folder_id'], image[
            'name']
    project_type = project["type"]
    if verbose:
        logger.info(
            "Uploading annotations for image %s in project %s.", image_name,
            project["name"]
        )
    annotation_classes = search_annotation_classes(
        project, return_metadata=True
    )
    annotation_classes_dict = get_annotation_classes_name_to_id(
        annotation_classes
    )
    fill_class_and_attribute_ids(annotation_json, annotation_classes_dict)
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'folder_id': folder_id
    }
    response = _api.send_request(
        req_type='GET',
        path=f'/image/{image_id}/annotation/getAnnotationUploadToken',
        params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't upload annotation. " + response.text
        )
    res = response.json()
    if project_type == 1:  # vector
        res = res['objects']
        s3_session = boto3.Session(
            aws_access_key_id=res['accessKeyId'],
            aws_secret_access_key=res['secretAccessKey'],
            aws_session_token=res['sessionToken']
        )
        s3_resource = s3_session.resource('s3')
        bucket = s3_resource.Bucket(res["bucket"])
        bucket.put_object(
            Key=res['filePath'], Body=json.dumps(annotation_json)
        )
    else:  # pixel
        if mask is None:
            raise SABaseException(0, "Pixel annotation should have mask.")
        if not isinstance(mask, io.BytesIO):
            with open(mask, "rb") as f:
                mask = io.BytesIO(f.read())
        res_j = res['pixel']
        s3_session = boto3.Session(
            aws_access_key_id=res_j['accessKeyId'],
            aws_secret_access_key=res_j['secretAccessKey'],
            aws_session_token=res_j['sessionToken']
        )
        s3_resource = s3_session.resource('s3')
        bucket = s3_resource.Bucket(res_j["bucket"])
        bucket.put_object(
            Key=res_j['filePath'], Body=json.dumps(annotation_json)
        )
        res_m = res['save']
        s3_session = boto3.Session(
            aws_access_key_id=res_m['accessKeyId'],
            aws_secret_access_key=res_m['secretAccessKey'],
            aws_session_token=res_m['sessionToken']
        )
        s3_resource = s3_session.resource('s3')
        bucket = s3_resource.Bucket(res_m["bucket"])
        bucket.put_object(Key=res_m['filePath'], Body=mask)


def create_fuse_image(
    image, classes_json, project_type, in_memory=False, output_overlay=False
):
    """Creates fuse for locally located image and annotations

    :param image: path to image
    :type image: str or Pathlike
    :param image_name: annotation classes or path to their JSON
    :type image: list or Pathlike
    :param project_type: project type, "Vector" or "Pixel"
    :type project_type: str
    :param in_memory: enables pillow Image return instead of saving the image
    :type in_memory: bool

    :return: path to created fuse image or pillow Image object if in_memory enabled
    :rtype: str of PIL.Image
    """
    annotation_path = image_path_to_annotation_paths(image, project_type)
    annotation_json = json.load(open(annotation_path[0]))
    if not isinstance(classes_json, list):
        classes_json = json.load(open(classes_json))
    class_color_dict = {}
    for ann_class in classes_json:
        if "name" not in ann_class:
            continue
        class_color_dict[ann_class["name"]] = ann_class["color"]
    pil_image = Image.open(image)
    image_size = pil_image.size
    fi = np.full((image_size[1], image_size[0], 4), [0, 0, 0, 255], np.uint8)
    if output_overlay:
        fi_ovl = np.full(
            (image_size[1], image_size[0], 4), [0, 0, 0, 255], np.uint8
        )
        fi_ovl[:, :, :3] = np.array(pil_image)
    if project_type == "Vector":
        fi_pil = Image.fromarray(fi)
        draw = ImageDraw.Draw(fi_pil)
        if output_overlay:
            fi_pil_ovl = Image.fromarray(fi_ovl)
            draw_ovl = ImageDraw.Draw(fi_pil_ovl)
        for annotation in annotation_json:
            if "className" not in annotation:
                continue
            color = class_color_dict[annotation["className"]]
            rgb = hex_to_rgb(color)
            fill_color = (rgb[0], rgb[1], rgb[2], 255)
            outline_color = (255, 255, 255, 255)
            if annotation["type"] == "bbox":
                pt = (
                    (annotation["points"]["x1"], annotation["points"]["y1"]),
                    (annotation["points"]["x2"], annotation["points"]["y2"])
                )
                draw.rectangle(pt, fill_color, outline_color)
                if output_overlay:
                    draw_ovl.rectangle(pt, None, fill_color)
            elif annotation["type"] == "polygon":
                pts = annotation["points"]
                draw.polygon(pts, fill_color, outline_color)
                if output_overlay:
                    draw_ovl.polygon(pts, None, fill_color)
            elif annotation["type"] == "polyline":
                pts = annotation["points"]
                draw.line(pts, fill_color, width=2)
                if output_overlay:
                    draw_ovl.line(pts, fill_color, width=2)
            elif annotation["type"] == "point":
                pts = [
                    annotation["x"] - 2, annotation["y"] - 2,
                    annotation["x"] + 2, annotation["y"] + 2
                ]
                draw.ellipse(pts, fill_color, outline_color)
                if output_overlay:
                    draw_ovl.ellipse(pts, None, fill_color)
            elif annotation["type"] == "ellipse":
                temp = np.full(
                    (image_size[1], image_size[0], 3), [0, 0, 0], np.uint8
                )
                if output_overlay:
                    temp_ovl = np.full(
                        (image_size[1], image_size[0], 3), [0, 0, 0], np.uint8
                    )
                    cv2.ellipse(
                        temp_ovl, (annotation["cx"], annotation["cy"]),
                        (annotation["rx"], annotation["ry"]),
                        annotation["angle"], 0, 360, fill_color[:-1], 1
                    )
                    new_array_ovl = np.array(fi_pil_ovl)
                    temp_mask = np.alltrue(temp_ovl != [0, 0, 0], axis=2)
                    new_array_ovl[:, :, :-1] = np.where(
                        temp_mask[:, :, np.newaxis], temp_ovl,
                        new_array_ovl[:, :, :-1]
                    )
                    fi_pil_ovl = Image.fromarray(new_array_ovl)
                    draw_ovl = ImageDraw.Draw(fi_pil_ovl)
                cv2.ellipse(
                    temp, (annotation["cx"], annotation["cy"]),
                    (annotation["rx"], annotation["ry"]), annotation["angle"],
                    0, 360, outline_color[:-1], 1
                )
                temp_mask = np.zeros(
                    (image_size[1] + 2, image_size[0] + 2), np.uint8
                )
                cv2.floodFill(
                    temp, temp_mask, (annotation["cx"], annotation["cy"]),
                    fill_color[:-1]
                )
                temp_mask = np.alltrue(temp != [0, 0, 0],
                                       axis=2).astype(np.uint8) * 255
                # print(temp_mask.shape, temp_mask.dtype, np.max(temp_mask))
                new_array = np.array(fi_pil)
                new_array[:, :, :-1] += temp
                new_array[:, :, 3] += temp_mask
                fi_pil = Image.fromarray(new_array)
                draw = ImageDraw.Draw(fi_pil)
            elif annotation["type"] == "template":
                pts = annotation["points"]
                pt_dict = {}
                for pt in pts:
                    pt_e = [pt["x"] - 2, pt["y"] - 2, pt["x"] + 2, pt["y"] + 2]
                    draw.ellipse(pt_e, fill_color, fill_color)
                    if output_overlay:
                        draw_ovl.ellipse(pt_e, fill_color, fill_color)
                    pt_dict[pt["id"]] = [pt["x"], pt["y"]]
                connections = annotation["connections"]
                for connection in connections:
                    draw.line(
                        pt_dict[connection["from"]] + pt_dict[connection["to"]],
                        fill_color,
                        width=1
                    )
                    if output_overlay:
                        draw_ovl.line(
                            pt_dict[connection["from"]] +
                            pt_dict[connection["to"]],
                            fill_color,
                            width=1
                        )
    else:
        annotation_mask = np.array(Image.open(annotation_path[1]))
        # print(annotation_mask.shape, annotation_mask.dtype)
        for annotation in annotation_json:
            if "className" not in annotation or "parts" not in annotation:
                continue
            color = class_color_dict[annotation["className"]]
            rgb = hex_to_rgb(color)
            fill_color = (rgb[0], rgb[1], rgb[2], 255)
            for part in annotation["parts"]:
                part_color = part["color"]
                part_color = list(hex_to_rgb(part_color)) + [255]
                temp_mask = np.alltrue(annotation_mask == part_color, axis=2)
                fi[temp_mask] = fill_color
        fi_pil = Image.fromarray(fi)

    if in_memory:
        if output_overlay:
            return (fi_pil, fi_pil_ovl)
        else:
            return (fi_pil, )
    fuse_path = str(image) + "___fuse.png"
    fi_pil.save(fuse_path)
    if output_overlay:
        overlay_path = str(image) + "___overlay.jpg"
        fi_pil_ovl.convert("RGB").save(overlay_path, subsampling=0, quality=100)
        return (fuse_path, overlay_path)
    else:
        return (fuse_path, )
