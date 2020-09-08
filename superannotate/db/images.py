import io
import json
import logging
from pathlib import Path

import boto3
import requests

from ..api import API
from ..common import annotation_status_str_to_int
from ..exceptions import SABaseException
from .annotation_classes import search_annotation_classes
from .projects import get_project_metadata

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()


def _get_project_type(project):
    """Get type of project
    Returns
    -------
    int
        1 = vector
        2 = pixel
    """
    return get_project_metadata(project)["type"]


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


def search_images(project, name_prefix=None, annotation_status=None):
    """Search images by name_prefix (case-insensitive) and annotation status

    :param project: project metadata in which the images are searched
    :type project: dict
    :param name_prefix: name prefix for search
    :type name_prefix: str
    :param annotation_status: if not None, annotation statuses of images to filter,
                              should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :return: metadata of found images
    :rtype: list of dicts
    """
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
    if name_prefix is not None:
        params['name'] = name_prefix
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
                result_list.append(r)
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


def set_image_annotation_status(image, annotation_status):
    """Sets the image annotation status

    :param image: image metadata
    :type image: dict
    :param annotation_status: annotation status to set,
           should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :return: metadata of the updated image
    :rtype: dict
    """
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


def add_image_annotation_bbox(image, bbox, annotation_class_name, error=None):
    """Add a bounding box annotation to image annotations

    :param project: metadata of the image
    :type project: dict
    :param bbox: 4 element list of top-left x,y and bottom-right x, y coordinates
    :type bbox: list of floats
    :param annotation_class_name: annotation class name
    :type annotation_class_name: str
    :param error: if not None, marks annotation as error (True) or no-error (False)
    :type error: bool
    """
    annotation = {
        "type": "bbox",
        "points": {
            "x1": bbox[0],
            "y1": bbox[1],
            "x2": bbox[2],
            "y2": bbox[3]
        },
        "className": annotation_class_name,
        "error": error,
        "groupId": 0,
        "pointLabels": {},
        "locked": False,
        "visible": True,
        "attributes": [],
    }
    annotations = get_image_annotations(image)["annotation_json"]
    if annotations is None:
        annotations = []
    annotations.append(annotation)
    upload_annotations_from_json_to_image(image, annotations, verbose=False)


def get_image_metadata(image):
    """Return up-to-date image metadata

    :param project: metadata of the image
    :type project: dict

    :return: metadata of image
    :rtype: dict
    """
    team_id, project_id, image_id = image["team_id"], image["project_id"
                                                           ], image["id"]
    params = {
        'team_id': team_id,
        'project_id': project_id,
    }
    response = _api.send_request(
        req_type='GET', path=f'/image/{image_id}', params=params
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    return response.json()


def download_image(
    image, local_dir_path=".", include_annotations=False, variant='original'
):
    """Downloads the image (and annotation if not None) to local_dir_path

    :param image: image metadata
    :type image: dict
    :param local_dir_path: where to download the image
    :type local_dir_path: Pathlike (str or Path)
    :param include_annotations: enables annotation download with the image
    :type include_annotations: bool
    :param variant: which resolution to download, can be 'original' or 'lores'
     (low resolution used in web editor)
    :type variant: str

    :return: paths of downloaded image and annotations if included
    :rtype: tuple
    """
    image_id, image_name = image["id"], image['name']
    if not Path(local_dir_path).is_dir():
        raise SABaseException(
            0, f"local_dir_path {local_dir_path} is not an existing directory"
        )
    img = get_image_bytes(image, variant=variant)
    if variant == "lores":
        image_name += "___lores.jpg"
    filepath = Path(local_dir_path) / image_name
    with open(filepath, 'wb') as f:
        f.write(img.getbuffer())
    annotations_filepaths = None
    if include_annotations:
        annotations_filepaths = download_image_annotations(
            image, local_dir_path
        )
    logger.info(
        "Downloaded image %s (ID %s) to %s", image_name, image_id, filepath
    )

    return (str(filepath), annotations_filepaths)


def get_image_bytes(image, variant='original'):
    """Returns an io.BytesIO() object of the image. Suitable for creating
    PIL.Image out of it.

    :param image: image metadata
    :type image: dict
    :param variant: which resolution to get, can be 'original' or 'lores'
     (low resolution)
    :type variant: str

    :return: io.BytesIO() of the image
    :rtype: io.BytesIO()
    """
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


def get_image_preannotations(image):
    """Get pre-annotations of the image. Only works for "vector" projects.

    :param image: image metadata
    :type image: dict

    :return: dict object with following keys:
        "preannotation_json": dict object of the annotation,
        "preannotation_json_filename": filename on server,
    :rtype: dict
    """
    team_id, project_id, image_id, folder_id = image["team_id"], image[
        "project_id"], image["id"], image['folder_id']
    project_metadata = {'id': project_id, 'team_id': team_id}
    project_type = _get_project_type(project_metadata)
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

    annotation_classes = search_annotation_classes(project_metadata)
    annotation_classes_dict = {}
    for annotation_class in annotation_classes:
        annotation_classes_dict[annotation_class["id"]] = annotation_class
    if project_type == 1:  # vector
        res = res['preannotation']
        url = res["url"]
        annotation_json_filename = url.rsplit('/', 1)[-1]
        headers = res["headers"]
        response = requests.get(url=url, headers=headers)
        if not response.ok:
            logger.warning("No preannotation available for image %s.", image_id)
            return {
                "preannotation_json_filename": None,
                "preannotation_json": None
            }
        res_json = response.json()
        for r in res_json:
            if r["classId"] in annotation_classes_dict:
                r["className"] = annotation_classes_dict[r["classId"]]["name"]

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
        for r in preannotation_json:
            if r["classId"] in annotation_classes_dict:
                r["className"] = annotation_classes_dict[r["classId"]]["name"]

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


def get_image_annotations(image, project_type=None):
    """Get annotations of the image.

    :param image: image metadata
    :type image: dict

    :return: dict object with following keys:
        "annotation_json": dict object of the annotation,
        "annotation_json_filename": filename on server,
        "annotation_mask": mask (for pixel),
        "annotation_mask_filename": mask filename on server
    :rtype: dict
    """
    team_id, project_id, image_id, folder_id = image["team_id"], image[
        "project_id"], image["id"], image['folder_id']
    if project_type is None:
        project_type = _get_project_type({'id': project_id, 'team_id': team_id})
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
    if project_type == 1:  # vector
        url = res["objects"]["url"]
        annotation_json_filename = url.rsplit('/', 1)[-1]
        headers = res["objects"]["headers"]
        response = requests.get(url=url, headers=headers)
        if response.ok:
            return {
                "annotation_json_filename": annotation_json_filename,
                "annotation_json": response.json()
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


def download_image_annotations(image, local_dir_path):
    """Downloads annotations of the image (JSON and mask if pixel type project)
    to local_dir_path.

    :param image: image metadata
    :type image: dict
    :param local_dir_path: local directory path to download to
    :type local_dir_path: Pathlike (str or Path)

    :return: paths of downloaded annotations
    :rtype: tuple
    """

    team_id, project_id = image["team_id"], image["project_id"]
    project_type = _get_project_type({'id': project_id, 'team_id': team_id})
    annotation = get_image_annotations(image, project_type)
    if annotation["annotation_json_filename"] is None:
        logger.info(
            "No annotation found for image %s (ID %s).", image["name"],
            image["id"]
        )
        return None
    return_filepaths = []
    json_path = Path(local_dir_path) / annotation["annotation_json_filename"]
    return_filepaths.append(str(json_path))
    if project_type == 1:
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


def download_image_preannotations(image, local_dir_path):
    """Downloads pre-annotations of the image to local_dir_path.
    Only works for "vector" projects.

    :param image: image metadata
    :type image: dict
    :param local_dir_path: local directory path to download to
    :type local_dir_path: Pathlike (str or Path)

    :return: paths of downloaded pre-annotations
    :rtype: tuple
    """
    team_id, project_id, = image["team_id"], image["project_id"]
    project_type = _get_project_type({'id': project_id, 'team_id': team_id})
    annotation = get_image_preannotations(image)
    if annotation["preannotation_json_filename"] is None:
        return (None, )
    return_filepaths = []
    json_path = Path(local_dir_path) / annotation["preannotation_json_filename"]
    return_filepaths.append(json_path)
    if project_type == 1:
        with open(json_path, "w") as f:
            json.dump(annotation["preannotation_json"], f)
    else:
        with open(
            Path(local_dir_path) / annotation["preannotation_json_filename"],
            "w"
        ) as f:
            json.dump(annotation["preannotation_json"], f)
        with open(
            Path(local_dir_path) / annotation["preannotation_mask_filename"],
            "wb"
        ) as f:
            f.write(annotation["preannotation_mask"].getbuffer())
    return tuple(return_filepaths)


def upload_annotations_from_file_to_image(
    image, json_path, mask_path=None, verbose=True
):
    """Upload annotations from json_path (also mask_path for pixel annotations)
    to the image.

    :param image: image metadata
    :type image: dict
    :param json_path: annotations in SuperAnnotate format json dict
    :type json_path: Pathlike (str or Path)
    :param mask_path: filepath to mask annotation for pixel projects in SuperAnnotate format
    :type mask_path: Pathlike (str or Path)
    """
    annotation_json = json.load(open(json_path))
    if verbose:
        logger.info("Uploading annotations from %s.", json_path)
    return upload_annotations_from_json_to_image(
        image, annotation_json, mask_path
    )


def upload_annotations_from_json_to_image(
    image, annotation_json, mask_path=None, verbose=True
):
    """Upload annotations from JSON (also mask_path for pixel annotations)
    to the image.

    :param image: image metadata
    :type image: dict
    :param annotation_json: annotations in SuperAnnotate format JSON dict
    :type annotation_json: dict
    :param mask_path: filepath to mask annotation for pixel projects in SuperAnnotate format
    :type mask_path: Pathlike (str or Path)
    """

    team_id, project_id, image_id, folder_id, image_name = image[
        "team_id"], image["project_id"], image["id"], image['folder_id'], image[
            'name']
    project = {'id': project_id, 'team_id': team_id}
    project_type = _get_project_type(project)
    if verbose:
        logger.info(
            "Uploading annotations for image %s in project %s.", image_name,
            project_id
        )
    annotation_classes = search_annotation_classes(project)
    annotation_classes_dict = {}
    for annotation_class in annotation_classes:
        if annotation_class["name"] in annotation_classes_dict:
            logger.warning(
                "Duplicate annotation class name %s. Only one of the annotation classes will be used. This will result in errors in annotation upload.",
                annotation_class["name"]
            )
        annotation_classes_dict[annotation_class["name"]] = annotation_class
    for ann in annotation_json:
        if "userId" in ann and ann["type"] == "meta":
            continue
        annotation_class_name = ann["className"]
        if not annotation_class_name in annotation_classes_dict:
            raise SABaseException(
                0, "Couldn't find annotation class " + annotation_class_name
            )
        class_id = annotation_classes_dict[annotation_class_name]["id"]
        ann["classId"] = class_id
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
    if response.ok:
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
            if mask_path is None:
                raise SABaseException(0, "Pixel annotation should have mask.")
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
            bucket.put_object(Key=res_m['filePath'], Body=open(mask_path, 'rb'))
    else:
        raise SABaseException(
            response.status_code, "Couldn't upload annotation. " + response.text
        )
