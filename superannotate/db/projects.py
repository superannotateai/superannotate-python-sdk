import io
import json
import logging
import math
import sys
import threading
import time
from pathlib import Path
import re

import boto3
from PIL import Image
from tqdm import tqdm

from ..api import API
from ..common import (
    annotation_status_str_to_int, project_type_int_to_str,
    project_type_str_to_int, user_role_str_to_int
)
from ..exceptions import SABaseException
from .annotation_classes import search_annotation_classes
from .images import get_image_metadata, delete_image, get_image_bytes

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()
_NUM_THREADS = 10

_RESIZE_CONFIG = {2: 4_000_000, 1: 100_000_000}  # 1: vector 2: pixel


def search_projects(name=None):
    """Project name based case-insensitive search for projects.
    Any project with name that contains string from **name** will be returned.
    If **name** is None, all the projects will be returned.

    :param name: search string
    :type name: str

    :return: dict objects representing found projects
    :rtype: list
    """
    result_list = []
    params = {'team_id': str(_api.team_id), 'offset': 0}
    if name is not None:
        params['name'] = name
    while True:
        response = _api.send_request(
            req_type='GET', path='/projects', params=params
        )
        if response.ok:
            new_results = response.json()
            result_list += new_results["data"]
            if response.json()["count"] <= len(result_list):
                break
            params["offset"] = len(result_list)
        else:
            raise SABaseException(
                response.status_code,
                "Couldn't search projects." + response.text
            )
    return result_list


def create_project(project_name, project_description, project_type):
    """Create a new project in the team.

    :param project_name: the new project's name
    :type project_name: str
    :param project_description: the new project's description
    :type project_description: str
    :param project_type: the new project type, Vector or Pixel.
    :type project_type: str

    :return: dict object representing the new project
    :rtype: dict
    """
    project_type = project_type_str_to_int(project_type)
    data = {
        "team_id": str(_api.team_id),
        "name": project_name,
        "description": project_description,
        "status": 0,
        "type": project_type
    }
    response = _api.send_request(
        req_type='POST', path='/project', json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't create project " + response.text
        )
    res = response.json()
    logger.info(
        "Created project %s (ID %s) with type %s", res["name"], res["id"],
        project_type_int_to_str(res["type"])
    )
    return res


def delete_project(project):
    """Deletes the project

    :param project: dict object representing project to be deleted
    :type project: dict
    """
    team_id, project_id = project["team_id"], project["id"]
    params = {"team_id": team_id}
    response = _api.send_request(
        req_type='DELETE', path=f'/project/{project_id}', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't delete project " + response.text
        )
    logger.info("Successfully deleted project with ID %s.", project_id)


def get_project_metadata(project):
    """Returns up-to-date project metadata

    :param project: metadata of the project
    :type project: dict

    :return: metadata of project
    :rtype: dict
    """
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': str(team_id)}
    response = _api.send_request(
        req_type='GET', path=f'/project/{project_id}', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get project." + response.text
        )
    res = response.json()
    return res


def get_project_image_count(project):
    """Returns number of images in the project.

    :param project: project metadata
    :type project: dict

    :return: number of images in the project
    :rtype: int
    """
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': team_id}
    response = _api.send_request(
        req_type='GET',
        path=f'/reporting/project/{project_id}/overview',
        params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't get project image count " + response.text
        )
    return response.json()["total_images"]


def upload_images_from_folder_to_project(
    project,
    folder_path,
    extensions=None,
    annotation_status="NotStarted",
    from_s3_bucket=None,
    exclude_file_patterns=None,
    recursive_subfolders=False,
    image_quality_in_editor=None
):
    """Uploads all images with given extensions from folder_path to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: metadata of the project to upload images
    :type project: dict
    :param folder_path: from which folder to upload the images
    :type folder_path: Pathlike (str or Path)
    :param extensions: list of filename extensions to include from folder, if None, then "jpg" and "png" are included
    :type extensions: list of str
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param exclude_file_patterns: filename patterns to exclude from uploading,
                                 default value is to exclude SuperAnnotate pixel project
                                 annotation mask output file pattern. If None,
                                 SuperAnnotate related ["___save.png", "___fuse.png"]
                                 will bet set as default exclude_file_patterns.
    :type exclude_file_patterns: list of strs
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool
    :param image_quality_in_editor: image quality (in percents) that will be seen in SuperAnnotate web annotation editor. If None default value will be used.
    :type image_quality_in_editor: int

    :return: uploaded images' filepaths
    :rtype: list
    """
    if recursive_subfolders:
        logger.warning(
            "When using recursive subfolder parsing same name images in different subfolders will overwrite each other."
        )
    if exclude_file_patterns is None:
        exclude_file_patterns = ["___save.png", "___fuse.png"]
    project_id = project["id"]
    if extensions is None:
        extensions = ["jpg", "png"]
    elif not isinstance(extensions, list):
        raise SABaseException(
            0,
            "extensions should be a list in upload_images_from_folder_to_project"
        )

    logger.info(
        "Uploading all images with extensions %s from %s to project ID %s.",
        extensions, folder_path, project_id
    )
    if from_s3_bucket is None:
        paths = []
        for extension in extensions:
            if not recursive_subfolders:
                paths += list(Path(folder_path).glob(f'*.{extension}'))
            else:
                paths += list(Path(folder_path).rglob(f'*.{extension}'))
    else:
        s3_client = boto3.client('s3')
        paginator = s3_client.get_paginator('list_objects_v2')
        response_iterator = paginator.paginate(
            Bucket=from_s3_bucket, Prefix=folder_path
        )

        paths = []
        for response in response_iterator:
            for object_data in response['Contents']:
                key = object_data['Key']
                if not recursive_subfolders and '/' in key[len(folder_path) +
                                                           1:]:
                    continue
                for extension in extensions:
                    if key.endswith(f'.{extension}'):
                        paths.append(key)
                        break
    filtered_paths = []
    for path in paths:
        not_in_exclude_list = [
            x not in Path(path).name for x in exclude_file_patterns
        ]
        if all(not_in_exclude_list):
            filtered_paths.append(path)

    return upload_images_to_project(
        project, filtered_paths, annotation_status, from_s3_bucket,
        image_quality_in_editor
    )


def get_image_array_to_upload(
    byte_io_orig, project_type, image_quality_in_editor
):
    im = Image.open(byte_io_orig)
    width, height = im.size
    max_size = _RESIZE_CONFIG[project_type]
    if (width * height) > max_size:
        max_size_root = math.sqrt(max_size)
        nwidth = math.floor(max_size_root * math.sqrt(width / height))
        nheight = math.floor(max_size_root * math.sqrt(height / width))
        print(nwidth, nheight)
        im = im.resize((nwidth, nheight))
        byte_io_orig = io.BytesIO()
        im.convert('RGB').save(
            byte_io_orig, im.format, subsampling=0, quality=100
        )

    byte_io_lores = io.BytesIO()
    im.convert('RGB').save(
        byte_io_lores,
        'JPEG',
        subsampling=0 if image_quality_in_editor > 60 else 2,
        quality=image_quality_in_editor
    )

    byte_io_thumbs = io.BytesIO()
    im.convert('RGB').resize((128, 96)).save(byte_io_thumbs, 'JPEG')

    byte_io_thumbs.seek(0)
    byte_io_lores.seek(0)
    byte_io_orig.seek(0)

    return byte_io_orig, byte_io_lores, byte_io_thumbs


def __upload_images_to_aws_thread(
    res,
    img_paths,
    project,
    annotation_status,
    prefix,
    thread_id,
    chunksize,
    already_uploaded,
    num_uploaded,
    image_quality_in_editor,
    from_s3_bucket=None,
):
    project_type = project["type"]
    len_img_paths = len(img_paths)
    start_index = thread_id * chunksize
    end_index = start_index + chunksize
    if from_s3_bucket is not None:
        from_session = boto3.Session()
        from_s3 = from_session.resource('s3')
    if start_index >= len_img_paths:
        return
    s3_session = boto3.Session(
        aws_access_key_id=res['accessKeyId'],
        aws_secret_access_key=res['secretAccessKey'],
        aws_session_token=res['sessionToken']
    )
    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(res["bucket"])
    prefix = res['filePath']
    uploaded_imgs = []
    for i in range(start_index, end_index):
        if i >= len_img_paths:
            break
        if already_uploaded[i]:
            continue
        path = img_paths[i]
        key = prefix + f'{Path(path).name}'
        if from_s3_bucket is not None:
            file = io.BytesIO()
            from_s3_object = from_s3.Object(from_s3_bucket, path)
            from_s3_object.download_fileobj(file)
        else:
            with open(path, "rb") as f:
                file = io.BytesIO(f.read())
        orig_image, lores_image, thumbnail_image = get_image_array_to_upload(
            file, project_type, image_quality_in_editor
        )
        try:
            bucket.put_object(Body=orig_image, Key=key)
        except Exception as e:
            logger.warning("Unable to upload orig_image to data server %s", e)
            break
        try:
            bucket.put_object(Body=lores_image, Key=key + '___lores.jpg')
        except Exception as e:
            logger.warning("Unable to upload lores_image to data server %s.", e)
            break
        try:
            bucket.put_object(Body=thumbnail_image, Key=key + '___thumb.jpg')
        except Exception as e:
            logger.warning(
                "Unable to upload thumbnail_image to data server %s.", e
            )
            break
        num_uploaded[thread_id] += 1
        already_uploaded[i] = True
        uploaded_imgs.append(path)
        if len(uploaded_imgs) >= 100:
            __create_image(uploaded_imgs, project, annotation_status, prefix)
            uploaded_imgs = []
    __create_image(uploaded_imgs, project, annotation_status, prefix)


def __create_image(img_paths, project, annotation_status, remote_dir):
    # print("Creating images ", len(img_paths))
    if len(img_paths) == 0:
        return
    team_id, project_id = project["team_id"], project["id"]
    data = {
        "project_id": str(project_id),
        "team_id": str(team_id),
        "images": [],
        "annotation_status": annotation_status
    }
    for img_path in img_paths:
        img_name = Path(img_path).name
        remote_path = remote_dir + f"{img_name}"
        data["images"].append({"name": img_name, "path": remote_path})

    response = _api.send_request(
        req_type='POST', path='/image/ext-create', json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't ext-create image " + response.text
        )


def upload_image_to_project(
    project,
    img,
    image_name=None,
    annotation_status="NotStarted",
    from_s3_bucket=None,
    image_quality_in_editor=None
):
    """Uploads image (io.BytesIO() or filepath to image) to project.
    Sets status of the uploaded image to set_status if it is not None.

    :param project: metadata of project to upload images to
    :type project: dict
    :param img: image to upload
    :type img: io.BytesIO() or Pathlike (str or Path)
    :param annotation_status: value to set the annotation statuses of the uploaded image NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param image_quality_in_editor: image quality (in percents) that will be seen in SuperAnnotate web annotation editor. If None default value will be used.
    :type image_quality_in_editor: int
    """
    annotation_status = annotation_status_str_to_int(annotation_status)
    if image_quality_in_editor is None:
        image_quality_in_editor = _get_project_default_image_quality_in_editor(
            project
        )

    img_name = None
    if not isinstance(img, io.BytesIO):
        img_name = Path(img).name
        if from_s3_bucket is not None:
            from_session = boto3.Session()
            from_s3 = from_session.resource('s3')
            from_s3_object = from_s3.Object(from_s3_bucket, img)
            img = io.BytesIO()
            from_s3_object.download_fileobj(img)
        else:
            with open(img, "rb") as f:
                img = io.BytesIO(f.read())
    if image_name is not None:
        img_name = image_name

    if img_name is None:
        raise SABaseException(
            0, "Image name img_name should be set if img is not Pathlike"
        )

    team_id, project_id = project["team_id"], project["id"]
    params = {
        'team_id': team_id,
    }
    response = _api.send_request(
        req_type='GET',
        path=f'/project/{project_id}/sdkImageUploadToken',
        params=params
    )
    if response.ok:
        res = response.json()
        prefix = res['filePath']
    else:
        raise SABaseException(
            response.status_code, "Couldn't get upload token " + response.text
        )
    s3_session = boto3.Session(
        aws_access_key_id=res['accessKeyId'],
        aws_secret_access_key=res['secretAccessKey'],
        aws_session_token=res['sessionToken']
    )
    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(res["bucket"])
    orig_image, lores_image, thumbnail_image = get_image_array_to_upload(
        img, project["type"], image_quality_in_editor
    )
    key = prefix + f'{img_name}'
    try:
        bucket.put_object(Body=orig_image, Key=key)
        bucket.put_object(Body=lores_image, Key=key + '___lores.jpg')
        bucket.put_object(Body=thumbnail_image, Key=key + '___thumb.jpg')
    except Exception as e:
        raise SABaseException(0, "Couldn't upload to data server. " + e)

    __create_image([img_name], project, annotation_status, prefix)

    while True:
        try:
            get_image_metadata(project, img_name)
        except SABaseException:
            time.sleep(0.2)
        else:
            break


def upload_images_to_project(
    project,
    img_paths,
    annotation_status="NotStarted",
    from_s3_bucket=None,
    image_quality_in_editor=None
):
    """Uploads all images given in list of path objects in img_paths to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: metadata of project to upload images to
    :type project: dict
    :param img_paths: list of Pathlike (str or Path) objects to upload
    :type img_paths: list
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param image_quality_in_editor: image quality (in percents) that will be seen in SuperAnnotate web annotation editor. If None default value will be used.
    :type image_quality_in_editor: int

    :return: uploaded images' filepaths
    :rtype: list of str
    """
    annotation_status = annotation_status_str_to_int(annotation_status)
    if image_quality_in_editor is None:
        image_quality_in_editor = _get_project_default_image_quality_in_editor(
            project
        )
    team_id, project_id = project["team_id"], project["id"]
    len_img_paths = len(img_paths)
    logger.info(
        "Uploading %s images to project ID %s.", len_img_paths, project_id
    )
    if len_img_paths == 0:
        return
    params = {
        'team_id': team_id,
    }
    num_uploaded = [0] * _NUM_THREADS
    already_uploaded = [False] * len_img_paths
    finish_event = threading.Event()
    chunksize = int(math.ceil(len(img_paths) / _NUM_THREADS))
    tqdm_thread = threading.Thread(
        target=__tqdm_thread, args=(len_img_paths, num_uploaded, finish_event)
    )
    tqdm_thread.start()
    while True:
        if sum(num_uploaded) == len_img_paths:
            break
        response = _api.send_request(
            req_type='GET',
            path=f'/project/{project_id}/sdkImageUploadToken',
            params=params
        )
        if response.ok:
            res = response.json()
            prefix = res['filePath']
        else:
            raise SABaseException(
                response.status_code,
                "Couldn't get upload token " + response.text
            )

        threads = []
        for thread_id in range(_NUM_THREADS):
            t = threading.Thread(
                target=__upload_images_to_aws_thread,
                args=(
                    res, img_paths, project, annotation_status, prefix,
                    thread_id, chunksize, already_uploaded, num_uploaded,
                    image_quality_in_editor, from_s3_bucket
                )
            )
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    finish_event.set()
    tqdm_thread.join()

    return_paths = [str(path) for path in img_paths]
    return return_paths


def __upload_annotations_thread(
    team_id, project_id, project_type, anns_filenames, folder_path,
    annotation_classes, thread_id, chunksize, num_uploaded, from_s3_bucket
):
    NUM_TO_SEND = 500
    len_anns = len(anns_filenames)
    start_index = thread_id * chunksize
    if start_index >= len_anns:
        return
    end_index = min(start_index + chunksize, len_anns)
    annotation_classes_dict = {}
    for annotation_class in annotation_classes:
        if annotation_class["name"] in annotation_classes_dict:
            logger.warning(
                "Duplicate annotation class name %s. Only one of the annotation classes will be used. This will result in errors in annotation upload.",
                annotation_class["name"]
            )
        annotation_classes_dict[annotation_class["name"]] = annotation_class

    postfix_json = '___objects.json' if project_type == 1 else '___pixel.json'
    len_postfix_json = len(postfix_json)
    postfix_mask = '___save.png'
    if from_s3_bucket is not None:
        from_session = boto3.Session()
        from_s3 = from_session.resource('s3')

    for i in range(start_index, end_index, NUM_TO_SEND):
        data = {"project_id": project_id, "team_id": team_id, "names": []}
        for j in range(i, i + NUM_TO_SEND):
            if j >= end_index:
                break
            image_name = anns_filenames[j][:-len_postfix_json]
            data["names"].append(image_name)
        response = _api.send_request(
            req_type='POST',
            path='/images/getAnnotationsPathsAndTokens',
            json_req=data
        )
        res = response.json()
        aws_creds = res["creds"]
        s3_session = boto3.Session(
            aws_access_key_id=aws_creds['accessKeyId'],
            aws_secret_access_key=aws_creds['secretAccessKey'],
            aws_session_token=aws_creds['sessionToken']
        )
        s3_resource = s3_session.resource('s3')
        bucket = s3_resource.Bucket(aws_creds["bucket"])

        for image_name, image_path in res['images'].items():
            json_filename = image_name + postfix_json
            if from_s3_bucket is None:
                annotation_json = json.load(
                    open(Path(folder_path) / json_filename)
                )
            else:
                file = io.BytesIO()
                from_s3_object = from_s3.Object(
                    from_s3_bucket, folder_path + json_filename
                )
                from_s3_object.download_fileobj(file)
                file.seek(0)
                annotation_json = json.load(file)

            for ann in annotation_json:
                if "userId" in ann and ann["type"] == "meta":
                    continue
                annotation_class_name = ann["className"]
                if not annotation_class_name in annotation_classes_dict:
                    logger.error(
                        "Couldn't find annotation class %s in project's annotation classes.",
                        annotation_class_name
                    )
                    sys.exit(1)
                class_id = annotation_classes_dict[annotation_class_name]["id"]
                ann["classId"] = class_id
            bucket.put_object(
                Key=image_path + postfix_json, Body=json.dumps(annotation_json)
            )
            if project_type != 1:
                mask_filename = image_name + postfix_mask
                if from_s3_bucket is None:
                    with open(Path(folder_path) / mask_filename, 'rb') as fin:
                        file = io.BytesIO(fin.read())
                else:
                    file = io.BytesIO()
                    from_s3_object = from_s3.Object(
                        from_s3_bucket, folder_path + mask_filename
                    )
                    from_s3_object.download_fileobj(file)
                    file.seek(0)
                bucket.put_object(Key=image_path + postfix_mask, Body=file)
            num_uploaded[thread_id] += 1


def upload_annotations_from_folder_to_project(
    project, folder_path, from_s3_bucket=None, recursive_subfolders=False
):
    """Finds and uploads all JSON files in the folder_path as annotations to the project.

    WARNING: The JSON files should follow specific naming convention. For Vector
    projects they should be named "<image_name>___objects.json", for Pixel projects
    JSON file should be named "<image_name>___pixel.json" and also second mask
    image file should be present with the name "<image_name>___save.png". In both cases
    image with <image_name> should be already present on the platform.

    WARNING: Existing annotations will be overwritten.

    :param project: metadata of the project to upload annotations to
    :type project: dict
    :param folder_path: from which folder to upload the annotations
    :type folder_path: Pathlike (str or Path)
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool

    :return: paths to annotations uploaded
    :rtype: list of strs
    """
    if recursive_subfolders:
        logger.warning(
            "When using recursive subfolder parsing same name annotations in different subfolders will overwrite each other."
        )

    logger.warning(
        "The JSON files should follow specific naming convention. For Vector projects they should be named '<image_name>___objects.json', for Pixel projects JSON file should be names '<image_name>___pixel.json' and also second mask image file should be present with the name '<image_name>___save.png'. In both cases image with <image_name> should be already present on the platform."
    )

    logger.warning("Existing annotations will be overwritten.")

    return _upload_annotations_from_folder_to_project(
        project, folder_path, from_s3_bucket, recursive_subfolders
    )


def _upload_annotations_from_folder_to_project(
    project, folder_path, from_s3_bucket=None, recursive_subfolders=False
):
    return_result = []
    if from_s3_bucket is not None:
        if not folder_path.endswith('/'):
            folder_path = folder_path + '/'
    if recursive_subfolders:
        if from_s3_bucket is None:
            for path in Path(folder_path).glob('*'):
                if path.is_dir():
                    return_result += _upload_annotations_from_folder_to_project(
                        project, path, from_s3_bucket, recursive_subfolders
                    )
        else:
            s3_client = boto3.client('s3')
            result = s3_client.list_objects(
                Bucket=from_s3_bucket, Prefix=folder_path, Delimiter='/'
            )
            results = result.get('CommonPrefixes')
            if results is not None:
                for o in results:
                    return_result += _upload_annotations_from_folder_to_project(
                        project, o.get('Prefix'), from_s3_bucket,
                        recursive_subfolders
                    )

    team_id, project_id, project_type = project["team_id"], project[
        "id"], project["type"]
    logger.info(
        "Uploading all annotations from %s to project ID %s.", folder_path,
        project_id
    )

    annotations_paths = []
    annotations_filenames = []
    if from_s3_bucket is None:
        for path in Path(folder_path).glob('*.json'):
            if path.name.endswith('___objects.json'
                                 ) or path.name.endswith('___pixel.json'):
                annotations_paths.append(path)
                annotations_filenames.append(path.name)
    else:
        s3_client = boto3.client('s3')
        paginator = s3_client.get_paginator('list_objects_v2')
        response_iterator = paginator.paginate(
            Bucket=from_s3_bucket, Prefix=folder_path
        )

        for response in response_iterator:
            for object_data in response['Contents']:
                key = object_data['Key']
                if '/' in key[len(folder_path) + 1:]:
                    continue
                if key.endswith('___objects.json'
                               ) or key.endswith('___pixel.json'):
                    annotations_paths.append(key)
                    annotations_filenames.append(Path(key).name)

    len_annotations_paths = len(annotations_paths)
    logger.info(
        "Uploading %s annotations to project ID %s.", len_annotations_paths,
        project_id
    )
    if len_annotations_paths == 0:
        return return_result
    num_uploaded = [0] * _NUM_THREADS
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=__tqdm_thread,
        args=(len_annotations_paths, num_uploaded, finish_event)
    )
    tqdm_thread.start()

    annotation_classes = search_annotation_classes(project)
    chunksize = int(math.ceil(len_annotations_paths / _NUM_THREADS))
    threads = []
    for thread_id in range(_NUM_THREADS):
        t = threading.Thread(
            target=__upload_annotations_thread,
            args=(
                team_id, project_id, project_type, annotations_filenames,
                folder_path, annotation_classes, thread_id, chunksize,
                num_uploaded, from_s3_bucket
            )
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    finish_event.set()
    tqdm_thread.join()
    logger.info("Number of annotations uploaded %s.", sum(num_uploaded))

    return return_result + [str(p) for p in annotations_paths]


def __upload_preannotations_thread(
    aws_creds, project_type, preannotations_filenames, folder_path,
    annotation_classes, thread_id, chunksize, num_uploaded, already_uploaded,
    from_s3_bucket
):
    len_preanns = len(preannotations_filenames)
    start_index = thread_id * chunksize
    if start_index >= len_preanns:
        return
    end_index = min(start_index + chunksize, len_preanns)
    s3_session = boto3.Session(
        aws_access_key_id=aws_creds['accessKeyId'],
        aws_secret_access_key=aws_creds['secretAccessKey'],
        aws_session_token=aws_creds['sessionToken']
    )
    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(aws_creds["bucket"])

    postfix_json = '___objects.json' if project_type == 1 else '___pixel.json'
    len_postfix_json = len(postfix_json)
    postfix_mask = '___save.png'
    if from_s3_bucket is not None:
        from_session = boto3.Session()
        from_s3 = from_session.resource('s3')

    annotation_classes_dict = {}
    for annotation_class in annotation_classes:
        if annotation_class["name"] in annotation_classes_dict:
            logger.warning(
                "Duplicate annotation class name %s. Only one of the annotation classes will be used. This will result in errors in annotation upload.",
                annotation_class["name"]
            )
        annotation_classes_dict[annotation_class["name"]] = annotation_class
    for i in range(start_index, end_index):
        if already_uploaded[i]:
            continue
        json_filename = preannotations_filenames[i]
        if from_s3_bucket is None:
            annotation_json = json.load(open(Path(folder_path) / json_filename))
        else:
            file = io.BytesIO()
            from_s3_object = from_s3.Object(
                from_s3_bucket, folder_path + json_filename
            )
            from_s3_object.download_fileobj(file)
            file.seek(0)
            annotation_json = json.load(file)

        for ann in annotation_json:
            if "userId" in ann and ann["type"] == "meta":
                continue
            annotation_class_name = ann["className"]
            if not annotation_class_name in annotation_classes_dict:
                logger.error(
                    "Couldn't find annotation class %s in project's annotation classes.",
                    annotation_class_name
                )
                sys.exit(1)
            class_id = annotation_classes_dict[annotation_class_name]["id"]
            ann["classId"] = class_id
        bucket.put_object(
            Key=aws_creds["filePath"] + f"/{json_filename}",
            Body=json.dumps(annotation_json)
        )
        if project_type != 1:
            mask_filename = json_filename[:-len_postfix_json] + postfix_mask
            if from_s3_bucket is None:
                with open(Path(folder_path) / mask_filename, 'rb') as fin:
                    file = io.BytesIO(fin.read())
            else:
                file = io.BytesIO()
                from_s3_object = from_s3.Object(
                    from_s3_bucket, folder_path + mask_filename
                )
                from_s3_object.download_fileobj(file)
                file.seek(0)
            bucket.put_object(
                Key=aws_creds['filePath'] + f'/{mask_filename}', Body=file
            )
        num_uploaded[thread_id] += 1
        already_uploaded[i] = True


def __tqdm_thread(total_num, current_nums, finish_event):
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(5)
            if not finished:
                pbar.update(sum(current_nums) - pbar.n)
            else:
                pbar.update(total_num - pbar.n)
                break


def upload_preannotations_from_folder_to_project(
    project, folder_path, from_s3_bucket=None, recursive_subfolders=False
):
    """Finds and uploads all JSON files in the folder_path as pre-annotations to the project.

    WARNING: The JSON files should follow specific naming convention. For Vector
    projects they should be named "<image_name>___objects.json", for Pixel projects
    JSON file should be named "<image_name>___pixel.json" and also second mask
    image file should be present with the name "<image_name>___save.png". In both cases
    image with <image_name> should be already present on the platform.

    WARNING: Existing pre-annotations will be overwritten.

    :param project: metadata of the project to upload pre-annotations to
    :type project: dict
    :param folder_path: from which folder to upload the pre-annotations
    :type folder_path: Pathlike (str or Path)
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool

    :return: paths to pre-annotations uploaded
    :rtype: list of strs
    """
    if recursive_subfolders:
        logger.warning(
            "When using recursive subfolder parsing same name pre-annotations in different subfolders will overwrite each other."
        )
    logger.warning(
        "The JSON files should follow specific naming convention. For Vector projects they should be named '<image_name>___objects.json', for Pixel projects JSON file should be names '<image_name>___pixel.json' and also second mask image file should be present with the name '<image_name>___save.png'. In both cases image with <image_name> should be already present on the platform."
    )

    logger.warning(
        "Identically named existing pre-annotations will be overwritten."
    )
    return _upload_preannotations_from_folder_to_project(
        project, folder_path, from_s3_bucket, recursive_subfolders
    )


def _upload_preannotations_from_folder_to_project(
    project, folder_path, from_s3_bucket=None, recursive_subfolders=False
):
    return_result = []
    if from_s3_bucket is not None:
        if not folder_path.endswith('/'):
            folder_path = folder_path + '/'
    if recursive_subfolders:
        if from_s3_bucket is None:
            for path in Path(folder_path).glob('*'):
                if path.is_dir():
                    return_result += _upload_preannotations_from_folder_to_project(
                        project, path, from_s3_bucket, recursive_subfolders
                    )
        else:
            s3_client = boto3.client('s3')
            result = s3_client.list_objects(
                Bucket=from_s3_bucket, Prefix=folder_path, Delimiter='/'
            )
            results = result.get('CommonPrefixes')
            if results is not None:
                for o in results:
                    return_result += _upload_preannotations_from_folder_to_project(
                        project, o.get('Prefix'), from_s3_bucket,
                        recursive_subfolders
                    )

    team_id, project_id, project_type = project["team_id"], project[
        "id"], project["type"]
    logger.info(
        "Uploading all preannotations from %s to project ID %s.", folder_path,
        project_id
    )

    preannotations_paths = []
    preannotations_filenames = []
    if from_s3_bucket is None:
        for path in Path(folder_path).glob('*.json'):
            if path.name.endswith('___objects.json'
                                 ) or path.name.endswith('___pixel.json'):
                preannotations_paths.append(path)
                preannotations_filenames.append(path.name)
    else:
        s3_client = boto3.client('s3')
        paginator = s3_client.get_paginator('list_objects_v2')
        response_iterator = paginator.paginate(
            Bucket=from_s3_bucket, Prefix=folder_path
        )

        for response in response_iterator:
            for object_data in response['Contents']:
                key = object_data['Key']
                if '/' in key[len(folder_path) + 1:]:
                    continue
                if key.endswith('___objects.json'
                               ) or key.endswith('___pixel.json'):
                    preannotations_paths.append(key)
                    preannotations_filenames.append(Path(key).name)

    len_preannotations_paths = len(preannotations_paths)
    logger.info(
        "Uploading %s preannotations to project ID %s.",
        len_preannotations_paths, project_id
    )
    if len_preannotations_paths == 0:
        return return_result
    params = {'team_id': team_id, 'creds_only': True, 'type': project_type}
    num_uploaded = [0] * _NUM_THREADS
    already_uploaded = [False] * len_preannotations_paths
    chunksize = int(math.ceil(len_preannotations_paths / _NUM_THREADS))
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=__tqdm_thread,
        args=(len_preannotations_paths, num_uploaded, finish_event)
    )
    tqdm_thread.start()
    annotation_classes = search_annotation_classes(project)
    while True:
        if sum(num_uploaded) == len_preannotations_paths:
            break
        response = _api.send_request(
            req_type='GET',
            path=f'/project/{project_id}/preannotation',
            params=params
        )
        if not response.ok:
            raise SABaseException(response.status_code, response.text)
        aws_creds = response.json()

        threads = []
        for thread_id in range(_NUM_THREADS):
            t = threading.Thread(
                target=__upload_preannotations_thread,
                args=(
                    aws_creds, project_type, preannotations_filenames,
                    folder_path, annotation_classes, thread_id, chunksize,
                    num_uploaded, already_uploaded, from_s3_bucket
                )
            )
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    finish_event.set()
    tqdm_thread.join()
    logger.info("Number of preannotations uploaded %s.", sum(num_uploaded))
    return return_result + [str(p) for p in preannotations_paths]


def share_project(project, user, user_role):
    """Share project with user.

    :param project: metadata of the project
    :type project: dict
    :param user: metadata of the user to share project with
    :type user: dict
    :param user_role: user role to apply, one of Admin , Annotator , QA , Customer , Viewer
    :type user_role: str
    """
    user_role = user_role_str_to_int(user_role)
    team_id, project_id = project["team_id"], project["id"]
    user_id = user["id"]
    json_req = {"user_id": user_id, "user_role": user_role}
    params = {'team_id': team_id}
    response = _api.send_request(
        req_type='POST',
        path=f'/project/{project_id}/share',
        params=params,
        json_req=json_req
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    logger.info(
        "Shared project ID %s with user ID %s and role %s", project_id, user_id,
        user_role
    )


def unshare_project(project, user):
    """Unshare (remove) user from project.

    :param project: metadata of the project
    :type project: dict
    :param user: metadata of the user to share project with
    :type user: dict
    """
    team_id, project_id = project["team_id"], project["id"]
    user_id = user["id"]
    json_req = {"user_id": user_id}
    params = {'team_id': team_id}
    response = _api.send_request(
        req_type='DELETE',
        path=f'/project/{project_id}/share',
        params=params,
        json_req=json_req
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    logger.info("Unshared project ID %s from user ID %s", project_id, user_id)


def upload_images_from_s3_bucket_to_project(
    project,
    accessKeyId,
    secretAccessKey,
    bucket_name,
    folder_path,
    image_quality_in_editor=None
):
    """Uploads all images from AWS S3 bucket to the project.

    :param project: metadata of the project to upload images
    :type project: dict
    :param accessKeyId: AWS S3 access key ID
    :type accessKeyId: str
    :param secretAccessKey: AWS S3 secret access key
    :type secretAccessKey: str
    :param bucket_name: AWS S3 bucket
    :type bucket_name: str
    :param folder_path: from which folder to upload the images
    :type folder_path: str
    :param image_quality_in_editor: image quality (in percents) that will be seen in SuperAnnotate web annotation editor, if None default value will be used
    :type image_quality_in_editor: int
    """
    if image_quality_in_editor is not None:
        old_quality = _get_project_default_image_quality_in_editor(project)
        _set_project_default_image_quality_in_editor(
            project, image_quality_in_editor
        )
    team_id, project_id = project["team_id"], project["id"]
    params = {
        "team_id": team_id,
    }
    data = {
        "accessKeyID": accessKeyId,
        "secretAccessKey": secretAccessKey,
        "bucketName": bucket_name,
        "folderName": folder_path
    }
    response = _api.send_request(
        req_type='POST',
        path=f'/project/{project_id}/get-image-s3-access-point',
        params=params,
        json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't upload to project from S3 " + response.text
        )
    logger.info("Waiting for S3 upload to finish.")
    while True:
        time.sleep(5)
        res = _get_upload_from_s3_bucket_to_project_status(project)
        if res["progress"] == '2':
            break
        if res["progress"] != "1":
            raise SABaseException(
                response.status_code,
                "Couldn't upload to project from S3 " + response.text
            )
    if image_quality_in_editor is not None:
        _set_project_default_image_quality_in_editor(project, old_quality)


def _get_upload_from_s3_bucket_to_project_status(project):
    team_id, project_id = project["team_id"], project["id"]
    params = {
        "team_id": team_id,
    }
    response = _api.send_request(
        req_type='GET',
        path=f'/project/{project_id}/getS3UploadStatus',
        params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't get upload to project from S3 status " + response.text
        )
    return response.json()


def _get_project_default_image_quality_in_editor(project):
    team_id, project_id = project["team_id"], project["id"]
    params = {
        "team_id": team_id,
    }
    response = _api.send_request(
        req_type='GET', path=f'/project/{project_id}/settings', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't get project default image quality " + response.text
        )
    for setting in response.json():
        if "attribute" in setting and setting["attribute"] == "ImageQuality":
            return setting["value"]
    return 60
    # raise SABaseException(
    #     response.status_code,
    #     "Couldn't get project default image quality " + response.text
    # )


def _set_project_default_image_quality_in_editor(project, quality):
    team_id, project_id = project["team_id"], project["id"]

    params = {
        "team_id": team_id,
    }
    response = _api.send_request(
        req_type='GET', path=f'/project/{project_id}/settings', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't set project default image quality " + response.text
        )

    image_quality_id = None
    for setting in response.json():
        if setting["attribute"] == "ImageQuality":
            image_quality_id = setting["id"]

    if image_quality_id is None:
        raise SABaseException(
            response.status_code,
            "Couldn't set project default image quality " + response.text
        )

    json_req = {
        "settings":
            [
                {
                    "id": image_quality_id,
                    "attribute": "ImageQuality",
                    "value": int(quality)
                }
            ]
    }
    response = _api.send_request(
        req_type='PUT',
        path=f'/project/{project_id}/settings',
        params=params,
        json_req=json_req
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't set project settings " + response.text
        )


def copy_image(source_project, image_name, destination_project):
    """Copy image to a project. The image's project is the same as destination
    project then the name will be changed to <image_name>_(<num>).<image_ext>,
    where <num> is the next available number deducted from project image list.

    :param source_project: source project metadata
    :type source_project: dict
    :param image_name: image name
    :type image: str
    :param destination_project: destination project metadata
    :type destination_project: dict
    """
    img_b = get_image_bytes(source_project, image_name)
    if source_project != destination_project:
        upload_image_to_project(destination_project, img_b, image_name)
        new_name = image_name
    else:
        extension = Path(image_name).suffix
        p = re.compile(r"_\([0-9]+\)\.")
        found_copied = False
        for m in p.finditer(image_name):

            if m.start() + len(m.group()
                              ) + len(extension) - 1 == len(image_name):
                num = int(m.group()[2:-2])
                found_copied = True
                break
        if not found_copied:
            num = 1
        while True:
            if found_copied:
                new_name = image_name[:m.start() +
                                      2] + str(num + 1) + ")" + extension
            else:
                new_name = Path(image_name).stem + f"_({num})" + extension
            try:
                get_image_metadata(destination_project, new_name)
            except SABaseException:
                break
            else:
                num += 1
        upload_image_to_project(destination_project, img_b, new_name)
    logger.info(
        "Copied image %s/%s to %s/%s.", source_project["name"], image_name,
        destination_project["name"], new_name
    )


def move_image(source_project, image_name, destination_project):
    """Move image from source_project to destination_project. source_project
    and destination_project cannot be the same.

    :param source_project: source project metadata
    :type source_project: dict
    :param image_name: image name
    :type image: str
    :param destination_project: destination project metadata
    :type destination_project: dict
    """
    if source_project == destination_project:
        raise SABaseException(
            0, "Cannot move image if source_project == destination_project."
        )
    copy_image(source_project, image_name, destination_project)
    delete_image(source_project, image_name)
    logger.info("Deleted image %s/%s.", source_project["name"], image_name)
