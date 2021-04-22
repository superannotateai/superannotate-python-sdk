import io
import json
import logging
from pathlib import Path

import boto3
import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw

from .. import common
from ..annotation_helpers import (
    add_annotation_bbox_to_json, add_annotation_comment_to_json,
    add_annotation_cuboid_to_json, add_annotation_ellipse_to_json,
    add_annotation_point_to_json, add_annotation_polygon_to_json,
    add_annotation_polyline_to_json, add_annotation_template_to_json,
    fill_in_missing
)
from ..api import API
from ..exceptions import SABaseException
from .annotation_classes import (
    fill_class_and_attribute_ids, fill_class_and_attribute_names,
    get_annotation_classes_id_to_name, get_annotation_classes_name_to_id,
    search_annotation_classes
)
from .project_api import get_project_and_folder_metadata, get_project_metadata_bare
from .utils import _get_boto_session_by_credentials

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()


def get_project_root_folder_id(project):
    """Get root folder ID
    Returns
    -------
    int
        Root folder ID
    """
    params = {
        'team_id': project['team_id'],
        'project_id': project['id'],
        'is_root': 1
    }
    response = _api.send_request(req_type='GET', path='/folders', params=params)
    if not response.ok:
        raise SABaseException(response.status_code, response.text)

    response = response.json()
    return response['data'][0]['id']


def search_images(
    project,
    image_name_prefix=None,
    annotation_status=None,
    return_metadata=False
):
    """Search images by name_prefix (case-insensitive) and annotation status

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    project, project_folder = get_project_and_folder_metadata(project)
    team_id, project_id = project["team_id"], project["id"]
    if annotation_status is not None:
        annotation_status = common.annotation_status_str_to_int(
            annotation_status
        )

    if project_folder is not None:
        project_folder_id = project_folder["id"]
    else:
        project_folder_id = get_project_root_folder_id(project)

    result_list = []
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'annotation_status': annotation_status,
        'offset': 0,
        'folder_id': project_folder_id
    }
    if image_name_prefix is not None:
        params['name'] = image_name_prefix
    total_got = 0
    total_images = 0
    while True:
        response = _api.send_request(
            req_type='GET', path='/images-folders', params=params
        )
        if not response.ok:
            raise SABaseException(
                response.status_code, "Couldn't search images " + response.text
            )
        response = response.json()
        images = response["images"]
        folders = response["folders"]

        results_images = images["data"]
        for r in results_images:
            if return_metadata:
                result_list.append(r)
            else:
                result_list.append(r["name"])

        total_images += len(results_images)
        if images["count"] <= total_images:
            break
        total_got += len(results_images) + len(folders["data"])
        params["offset"] = total_got

    if return_metadata:

        def process_result(x):
            x["annotation_status"] = common.annotation_status_int_to_str(
                x["annotation_status"]
            )
            return x

        return list(map(process_result, result_list))
    else:
        return result_list


def search_images_all_folders(
    project,
    image_name_prefix=None,
    annotation_status=None,
    return_metadata=False
):
    """Search images by name_prefix (case-insensitive) and annotation status in 
    project and all of its folders

    :param project: project name
    :type project: str
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
    project = get_project_metadata_bare(project)
    team_id, project_id = project["team_id"], project["id"]
    if annotation_status is not None:
        annotation_status = common.annotation_status_str_to_int(
            annotation_status
        )

    project_folder_id = get_project_root_folder_id(project)

    result_list = []
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'annotation_status': annotation_status,
        'offset': 0,
        'folder_id': project_folder_id
    }
    if image_name_prefix is not None:
        params['name'] = image_name_prefix
    total_images = 0
    while True:
        response = _api.send_request(
            req_type='GET', path='/images', params=params
        )
        if not response.ok:
            raise SABaseException(
                response.status_code, "Couldn't search images " + response.text
            )
        response = response.json()
        results_images = response["data"]
        for r in results_images:
            if return_metadata:
                result_list.append(r)
            else:
                result_list.append(r["name"])

        total_images += len(results_images)
        if response["count"] <= total_images:
            break
        params["offset"] = total_images

    if return_metadata:

        def process_result(x):
            x["annotation_status"] = common.annotation_status_int_to_str(
                x["annotation_status"]
            )
            return x

        return list(map(process_result, result_list))
    else:
        return result_list


def get_image_metadata(project, image_names, return_dict_on_single_output=True):
    """Returns image metadata

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str

    :return: metadata of image
    :rtype: dict
    """
    project, project_folder = get_project_and_folder_metadata(project)
    if isinstance(image_names, str):
        image_names = [image_names]

    if project_folder is not None:
        project_folder_id = project_folder["id"]
    else:
        project_folder_id = None

    chunk_size = 500
    chunks = [
        image_names[i:i + chunk_size]
        for i in range(0, len(image_names), chunk_size)
    ]

    json_req = {
        'project_id': project['id'],
        'team_id': _api.team_id,
    }

    if project_folder_id is not None:
        json_req["folder_id"] = project_folder_id

    metadata_raw = []
    for chunk in chunks:
        json_req['names'] = chunk
        response = _api.send_request(
            req_type='POST',
            path='/images/getBulk',
            json_req=json_req,
        )
        if not response.ok:
            raise SABaseException(
                response.status_code,
                "Couldn't get image metadata. " + response.text
            )
        metadata_raw += response.json()

    metadata_without_deleted = []
    metadata_without_deleted = [i for i in metadata_raw if i['delete'] != 1]

    if len(metadata_without_deleted) == 0:
        raise SABaseException(
            0,
            f"None of the images in {image_names} exist in the provided project"
        )
    for item in metadata_without_deleted:
        item['annotation_status'] = common.annotation_status_int_to_str(
            item['annotation_status']
        )
        item['prediction_status'
            ] = common.prediction_segmentation_status_from_int_to_str(
                item['prediction_status']
            )
        item['segmentation_status'
            ] = common.prediction_segmentation_status_from_int_to_str(
                item['segmentation_status']
            )

    if len(metadata_without_deleted) == 1 and return_dict_on_single_output:
        return metadata_without_deleted[0]
    return metadata_without_deleted


def set_image_annotation_status(project, image_name, annotation_status):
    """Sets the image annotation status

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image_name: str
    :param annotation_status: annotation status to set,
           should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :return: metadata of the updated image
    :rtype: dict
    """
    image = get_image_metadata(project, image_name)
    team_id, project_id, image_id = image["team_id"], image["project_id"
                                                           ], image["id"]
    annotation_status = common.annotation_status_str_to_int(annotation_status)
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

    response = response.json()

    return response


def add_annotation_comment_to_image(
    project,
    image_name,
    comment_text,
    comment_coords,
    comment_author,
    resolved=False
):
    """Add a comment to SuperAnnotate format annotation JSON

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    upload_image_annotations(project, image_name, annotations, verbose=False)


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    upload_image_annotations(project, image_name, annotations, verbose=False)


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    upload_image_annotations(project, image_name, annotations, verbose=False)


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    upload_image_annotations(project, image_name, annotations, verbose=False)


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    upload_image_annotations(project, image_name, annotations, verbose=False)


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    upload_image_annotations(project, image_name, annotations, verbose=False)


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    upload_image_annotations(project, image_name, annotations, verbose=False)


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    upload_image_annotations(project, image_name, annotations, verbose=False)


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    if (include_fuse or include_overlay) and not include_annotations:
        raise SABaseException(
            0,
            "To download fuse or overlay image need to set include_annotations=True in download_image"
        )
    if not Path(local_dir_path).is_dir():
        raise SABaseException(
            0, f"local_dir_path {local_dir_path} is not an existing directory"
        )
    if variant not in ["original", "lores"]:
        raise SABaseException(
            0, "Image download variant should be either original or lores"
        )

    project, project_folder = get_project_and_folder_metadata(project)
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
    img = get_image_bytes(
        (project, project_folder), image_name, variant=variant
    )
    filepath_save = image_name
    if variant == "lores":
        filepath_save += "___lores.jpg"
    filepath_save = Path(local_dir_path) / filepath_save
    with open(filepath_save, 'wb') as f:
        f.write(img.getbuffer())
    annotations_filepaths = None
    fuse_path = None
    if include_annotations:
        annotations_filepaths = download_image_annotations(
            (project, project_folder), image_name, local_dir_path
        )
        if annotations_filepaths is not None and (
            include_fuse or include_overlay
        ):
            classes = search_annotation_classes(project)
            fuse_path = create_fuse_image(
                filepath_save,
                classes,
                project["type"],
                output_overlay=include_overlay
            )
    logger.info("Downloaded image %s to %s.", image_name, filepath_save)

    return (str(filepath_save), annotations_filepaths, fuse_path)


def delete_image(project, image_name):
    """Deletes image

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param variant: which resolution to get, can be 'original' or 'lores'
     (low resolution)
    :type variant: str

    :return: io.BytesIO() of the image
    :rtype: io.BytesIO()
    """
    project, project_folder = get_project_and_folder_metadata(project)
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
    if variant not in ["original", "lores"]:
        raise SABaseException(
            0, "Image download variant should be either original or lores"
        )
    image = get_image_metadata((project, project_folder), image_name)
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
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't download image" + response.text
        )
    img = io.BytesIO(response.content)
    return img


def get_image_preannotations(project, image_name):
    """Get pre-annotations of the image. Only works for "vector" projects.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str

    :return: dict object with following keys:
        "preannotation_json": dict object of the annotation,
        "preannotation_json_filename": filename on server,
        "preannotation_mask": mask (for pixel),
        "preannotation_mask_filename": mask filename on server
    :rtype: dict
    """
    return _get_image_pre_or_annotations(project, image_name, "pre")


def get_image_annotations(project, image_name):
    """Get annotations of the image.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str

    :return: dict object with following keys:
        "annotation_json": dict object of the annotation,
        "annotation_json_filename": filename on server,
        "annotation_mask": mask (for pixel),
        "annotation_mask_filename": mask filename on server
    :rtype: dict
    """
    return _get_image_pre_or_annotations(project, image_name, "")


def _get_image_pre_or_annotations(project, image_name, pre):
    project, project_folder = get_project_and_folder_metadata(project)
    image = get_image_metadata((project, project_folder), image_name, True)
    team_id, project_id, image_id, project_folder_id = image["team_id"], image[
        "project_id"], image["id"], image['folder_id']
    project_type = project["type"]
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'folder_id': project_folder_id
    }
    response = _api.send_request(
        req_type='GET',
        path=f'/image/{image_id}/annotation/getAnnotationDownloadToken',
        params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't get annotation download token" + response.text
        )
    res = response.json()
    # print(json.dumps(res, indent=2))

    annotation_classes = search_annotation_classes(project)
    annotation_classes_dict = get_annotation_classes_id_to_name(
        annotation_classes
    )
    loc = "MAIN" if pre == "" else "PREANNOTATION"
    if loc not in res["annotations"]:
        logger.warning("%sannotation doesn't exist for %s.", pre, image_name)
        return {
            f"{pre}annotation_json": None,
            f"{pre}annotation_json_filename": None,
            f"{pre}annotation_mask": None,
            f"{pre}annotation_mask_filename": None
        }
    main_annotations = res["annotations"][loc][0]
    response = requests.get(
        url=main_annotations["annotation_json_path"]["url"],
        headers=main_annotations["annotation_json_path"]["headers"]
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't load annotations" + response.text
        )
    res_json = response.json()
    fill_class_and_attribute_names(res_json, annotation_classes_dict)
    result = {
        f"{pre}annotation_json":
            res_json,
        f"{pre}annotation_json_filename":
            common.get_annotation_json_name(image_name, project_type)
    }
    if project_type == "Pixel":
        if main_annotations["annotation_bluemap_path"]["exist"]:
            response = requests.get(
                url=main_annotations["annotation_bluemap_path"]["url"],
                headers=main_annotations["annotation_bluemap_path"]["headers"]
            )
            if not response.ok:
                raise SABaseException(
                    response.status_code,
                    "Couldn't load annotations" + response.text
                )
            mask = io.BytesIO(response.content)
            result[f"{pre}annotation_mask"] = mask
            result[f"{pre}annotation_mask_filename"
                  ] = common.get_annotation_png_name(image_name)
        else:
            result.update(
                {
                    f"{pre}annotation_mask": None,
                    f"{pre}annotation_mask_filename": None
                }
            )

    fill_in_missing(result[f"{pre}annotation_json"])
    return result


def download_image_annotations(project, image_name, local_dir_path):
    """Downloads annotations of the image (JSON and mask if pixel type project)
    to local_dir_path.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param local_dir_path: local directory path to download to
    :type local_dir_path: Pathlike (str or Path)

    :return: paths of downloaded annotations
    :rtype: tuple
    """
    return _download_image_pre_or_annotations(
        project, image_name, local_dir_path, ""
    )


def _download_image_pre_or_annotations(
    project, image_name, local_dir_path, pre
):
    project, project_folder = get_project_and_folder_metadata(project)

    annotation = _get_image_pre_or_annotations(
        (project, project_folder), image_name, pre
    )

    if annotation[f"{pre}annotation_json_filename"] is None:
        image = get_image_metadata((project, project_folder), image_name)
        logger.warning(
            "No %sannotation found for image %s.", pre, image["name"]
        )
        return None
    return_filepaths = []
    json_path = Path(local_dir_path
                    ) / annotation[f"{pre}annotation_json_filename"]
    return_filepaths.append(str(json_path))
    if project["type"] == "Vector":
        with open(json_path, "w") as f:
            json.dump(annotation[f"{pre}annotation_json"], f, indent=4)
    else:
        with open(json_path, "w") as f:
            json.dump(annotation[f"{pre}annotation_json"], f, indent=4)
        if annotation[f"{pre}annotation_mask_filename"] is not None:
            mask_path = Path(local_dir_path
                            ) / annotation[f"{pre}annotation_mask_filename"]
            with open(mask_path, "wb") as f:
                f.write(annotation[f"{pre}annotation_mask"].getbuffer())
        else:
            mask_path = None
        return_filepaths.append(str(mask_path))

    return tuple(return_filepaths)


def download_image_preannotations(project, image_name, local_dir_path):
    """Downloads pre-annotations of the image to local_dir_path.
    Only works for "vector" projects.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param local_dir_path: local directory path to download to
    :type local_dir_path: Pathlike (str or Path)

    :return: paths of downloaded pre-annotations
    :rtype: tuple
    """
    return _download_image_pre_or_annotations(
        project, image_name, local_dir_path, "pre"
    )


def upload_image_annotations(
    project, image_name, annotation_json, mask=None, verbose=True
):
    """Upload annotations from JSON (also mask for pixel annotations)
    to the image.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param annotation_json: annotations in SuperAnnotate format JSON dict or path to JSON file
    :type annotation_json: dict or Pathlike (str or Path)
    :param mask: BytesIO object or filepath to mask annotation for pixel projects in SuperAnnotate format
    :type mask: BytesIO or Pathlike (str or Path)
    """

    if isinstance(annotation_json, list):
        raise SABaseException(
            0,
            "Annotation JSON should be a dict object. You are using list object. If this is an old annotation format you can convert it to new format with superannotate.update_json_format SDK function"
        )
    if not isinstance(annotation_json, dict):
        if verbose:
            logger.info("Uploading annotations from %s.", annotation_json)
        annotation_json = json.load(open(annotation_json))
    project, project_folder = get_project_and_folder_metadata(project)
    image = get_image_metadata((project, project_folder), image_name)
    team_id, project_id, image_id, folder_id, image_name = image[
        "team_id"], image["project_id"], image["id"], image['folder_id'], image[
            'name']
    project_type = project["type"]
    if verbose:
        logger.info(
            "Uploading annotations for image %s in project %s.", image_name,
            project["name"]
        )
    annotation_classes = search_annotation_classes(project)
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
    res_json = res['annotation_json_path']
    s3_session = _get_boto_session_by_credentials(res_json)
    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(res_json["bucket"])
    bucket.put_object(
        Key=res_json['filePath'], Body=json.dumps(annotation_json)
    )
    if project_type == "Pixel":
        if mask is None:
            raise SABaseException(0, "Pixel annotation should have mask.")
        if not isinstance(mask, io.BytesIO):
            with open(mask, "rb") as f:
                mask = io.BytesIO(f.read())
        res_mask = res['annotation_bluemap_path']
        s3_session = _get_boto_session_by_credentials(res_mask)
        bucket = s3_resource.Bucket(res_mask["bucket"])
        bucket.put_object(Key=res_mask['filePath'], Body=mask)


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
    annotation_path = common.image_path_to_annotation_paths(image, project_type)
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
        fi_pil_ovl = Image.fromarray(fi_ovl)
        draw_ovl = ImageDraw.Draw(fi_pil_ovl)
    if project_type == "Vector":
        fi_pil = Image.fromarray(fi)
        draw = ImageDraw.Draw(fi_pil)
        for annotation in annotation_json["instances"]:
            if "className" not in annotation:
                continue
            color = class_color_dict[annotation["className"]]
            rgb = common.hex_to_rgb(color)
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
        for annotation in annotation_json["instances"]:
            if "className" not in annotation or "parts" not in annotation:
                continue
            color = class_color_dict[annotation["className"]]
            rgb = common.hex_to_rgb(color)
            fill_color = (rgb[0], rgb[1], rgb[2], 255)
            for part in annotation["parts"]:
                part_color = part["color"]
                part_color = list(common.hex_to_rgb(part_color)) + [255]
                temp_mask = np.alltrue(annotation_mask == part_color, axis=2)
                fi[temp_mask] = fill_color
        fi_pil = Image.fromarray(fi)
        alpha = 0.5  # transparency measure
        if output_overlay:
            fi_pil_ovl = Image.fromarray(
                cv2.addWeighted(fi, alpha, fi_ovl, 1 - alpha, 0)
            )

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


def set_images_annotation_statuses(project, image_names, annotation_status):
    """Sets annotation statuses of images

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_names: image names. If None, all the images in the project will be used
    :type image_names: list of str
    :param annotation_status: annotation status to set,
           should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    """
    NUM_TO_SEND = 500
    project, project_folder = get_project_and_folder_metadata(project)
    params = {"team_id": project["team_id"], "project_id": project["id"]}
    annotation_status = common.annotation_status_str_to_int(annotation_status)
    data = {"annotation_status": annotation_status}
    if project_folder is not None:
        data["folder_id"] = project_folder["id"]
    if image_names is None:
        image_names = search_images((project, project_folder))
    for start_index in range(0, len(image_names), NUM_TO_SEND):
        data["image_names"] = image_names[start_index:start_index + NUM_TO_SEND]
        response = _api.send_request(
            req_type='PUT',
            path='/image/updateAnnotationStatusBulk',
            params=params,
            json_req=data
        )
        if not response.ok:
            raise SABaseException(
                response.status_code,
                "Couldn't change annotation statuses " + response.text
            )
    logger.info("Annotations status of images changed")