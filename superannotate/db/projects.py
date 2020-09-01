import io
import json
import logging
import math
import threading
import time
from pathlib import Path

import boto3
from PIL import Image
from tqdm import tqdm

from ..api import API
from ..common import (
    annotation_status_str_to_int, project_type_str_to_int,
    project_type_int_to_str, user_role_str_to_int
)
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()
_NUM_THREADS = 10

_RESIZE_CONFIG = {2: 4000000, 1: 100000000}  # 1: vector 2: pixel


def search_projects(name_prefix=None):
    """Project name based case-insensitive prefix search for projects.
    If name_prefix is None all the projects will be returned.

    :param name_prefix: name prefix for search
    :type name_prefix: str

    :return: dict objects representing found projects
    :rtype: list
    """
    result_list = []
    params = {'team_id': str(_api.team_id), 'offset': 0}
    if name_prefix is not None:
        params['name'] = name_prefix
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
    exclude_file_pattern="___save.png"
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
    :param exclude_file_pattern: filename pattern to exclude from uploading
    :type exclude_file_pattern: str

    :return: uploaded images' filepaths
    :rtype: list
    """
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
            paths += list(Path(folder_path).glob(f'*.{extension}'))
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
                if '/' in key[len(folder_path) + 1:]:
                    continue
                for extension in extensions:
                    if key.endswith(f'.{extension}'):
                        paths.append(key)
                        break
    filtered_paths = []
    for path in paths:
        if exclude_file_pattern not in Path(path).name:
            filtered_paths.append(path)

    return upload_images_to_project(
        project, filtered_paths, annotation_status, from_s3_bucket
    )


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
    from_s3_bucket=None
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
            file.seek(0)
            im = Image.open(file)
        else:
            im = Image.open(path)
        width, height = im.size
        max_size = _RESIZE_CONFIG[project_type]
        if (width * height) > max_size:
            max_size_root = math.sqrt(max_size)
            nwidth = math.floor(max_size_root * math.sqrt(width / height))
            nheight = math.floor(max_size_root * math.sqrt(height / width))
            im = im.resize((nwidth, nheight))
        byte_io = io.BytesIO()
        im.convert('RGB').save(byte_io, 'JPEG')
        byte_io.seek(0)
        try:
            bucket.put_object(Body=byte_io, Key=key, ContentType="image/jpeg")
        except Exception as e:
            logger.warning("Unable to upload to data server %s", e)
            break
        byte_io = io.BytesIO()
        im.convert('RGB').save(byte_io, 'JPEG', dpi=(96, 96))
        byte_io.seek(0)
        try:
            bucket.put_object(
                Body=byte_io,
                Key=key + '___lores.jpg',
                ContentType="image/jpeg"
            )
        except Exception as e:
            logger.warning("Unable to upload to data server %s", e)
            break
        byte_io = io.BytesIO()
        im.convert('RGB').resize((128, 96)).save(byte_io, 'JPEG', dpi=(96, 96))
        byte_io.seek(0)
        try:
            bucket.put_object(
                Body=byte_io,
                Key=key + '___thumb.jpg',
                ContentType="image/jpeg"
            )
        except Exception as e:
            logger.warning("Unable to upload to data server %s", e)
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


def upload_images_to_project(
    project, img_paths, annotation_status="NotStarted", from_s3_bucket=None
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

    :return: uploaded images' filepaths
    :rtype: list of str
    """
    annotation_status = annotation_status_str_to_int(annotation_status)
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
                    from_s3_bucket
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
    classid_conversion, thread_id, chunksize, num_uploaded, from_s3_bucket
):
    NUM_TO_SEND = 500
    len_anns = len(anns_filenames)
    start_index = thread_id * chunksize
    if start_index >= len_anns:
        return
    end_index = min(start_index + chunksize, len_anns)

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
                    from_s3_bucket, folder_path + '/' + json_filename
                )
                from_s3_object.download_fileobj(file)
                file.seek(0)
                annotation_json = json.load(file)

            if classid_conversion is not None:
                for ann in annotation_json:
                    if 'classId' not in ann:
                        continue
                    if ann['classId'] == -1:
                        continue
                    old_id = ann["classId"]
                    if old_id in classid_conversion:
                        new_id = classid_conversion[old_id]
                        ann["classId"] = new_id
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
                        from_s3_bucket, folder_path + '/' + mask_filename
                    )
                    from_s3_object.download_fileobj(file)
                    file.seek(0)
                bucket.put_object(Key=image_path + postfix_mask, Body=file)
            num_uploaded[thread_id] += 1


def upload_annotations_from_folder_to_project(
    project, folder_path, classid_conversion=None, from_s3_bucket=None
):
    """Finds and uploads all JSON files in the folder_path as annotations to the project.

    WARNING: The JSON files should follow specific naming convention. For Vector
    projects they should be named "<image_name>___objects.json", for Pixel projects
    JSON file should be named "<image_name>___pixel.json" and also second mask
    image file should be present with the name "<image_name>___save.png". In both cases
    image with <image_name> should be already present on the platform.

    WARNING: Create annotation classes with create_annotation_classes_from_classes_json or
    create_annotation_class before calling this function to have access to new
    class IDs after calling mentioned functions. Please see
    warning in the docstring of create_annotation_classes_from_classes_json.

    :param project: metadata of the project to upload annotations to
    :type project: dict
    :param folder_path: from which folder to upload the annotations
    :type folder_path: Pathlike (str or Path)
    :param classid_conversion: if not None, then class ID-es of the annotations
                               will be translated according to this dict during
                               the upload. This dict can be got when uploading
                               classes.json with create_annotation_classes_from_classes_json
    :type classid_conversion: dict
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str

    :return: paths to annotations uploaded
    :rtype: list of strs
    """
    team_id, project_id, project_type = project["team_id"], project[
        "id"], project["type"]
    logger.info(
        "Uploading all annotations from %s to project ID %s.", folder_path,
        project_id
    )
    logger.warning(
        "Create annotation classes with create_annotation_classes_from_classes_json or create_annotation_class before calling this function to have access to new class IDs after calling mentioned functions. Please see warning in the docstring of create_annotation_classes_from_classes_json."
    )

    logger.warning(
        "The JSON files should follow specific naming convention. For Vector projects they should be named '<image_name>___objects.json', for Pixel projects JSON file should be names '<image_name>___pixel.json' and also second mask image file should be present with the name '<image_name>___save.png'. In both cases image with <image_name> should be already present on the platform."
    )

    if from_s3_bucket is None:
        annotations_paths = list(Path(folder_path).glob('*.json'))
        annotations_filenames = [x.name for x in annotations_paths]
    else:
        s3_client = boto3.client('s3')
        paginator = s3_client.get_paginator('list_objects_v2')
        response_iterator = paginator.paginate(
            Bucket=from_s3_bucket, Prefix=folder_path
        )

        annotations_paths = []
        for response in response_iterator:
            for object_data in response['Contents']:
                key = object_data['Key']
                if '/' in key[len(folder_path) + 1:]:
                    continue
                if key.endswith('.json'):
                    annotations_paths.append(key)
        annotations_filenames = [Path(x).name for x in annotations_paths]

    len_annotations_paths = len(annotations_paths)
    logger.info(
        "Uploading %s annotations to project ID %s.", len_annotations_paths,
        project_id
    )
    if len_annotations_paths == 0:
        return
    num_uploaded = [0] * _NUM_THREADS
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=__tqdm_thread,
        args=(len_annotations_paths, num_uploaded, finish_event)
    )
    tqdm_thread.start()

    chunksize = int(math.ceil(len_annotations_paths / _NUM_THREADS))
    threads = []
    for thread_id in range(_NUM_THREADS):
        t = threading.Thread(
            target=__upload_annotations_thread,
            args=(
                team_id, project_id, project_type, annotations_filenames,
                folder_path, classid_conversion, thread_id, chunksize,
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

    return [str(p) for p in annotations_paths]


def __upload_preannotations_thread(
    aws_creds, project_type, preannotations_filenames, folder_path,
    classid_conversion, thread_id, chunksize, num_uploaded, already_uploaded,
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

    for i in range(start_index, end_index):
        if already_uploaded[i]:
            continue
        json_filename = preannotations_filenames[i]
        if from_s3_bucket is None:
            annotation_json = json.load(open(Path(folder_path) / json_filename))
        else:
            file = io.BytesIO()
            from_s3_object = from_s3.Object(
                from_s3_bucket, folder_path + '/' + json_filename
            )
            from_s3_object.download_fileobj(file)
            file.seek(0)
            annotation_json = json.load(file)

        if classid_conversion is not None:
            for ann in annotation_json:
                if 'classId' not in ann:
                    continue
                if ann['classId'] == -1:
                    continue
                old_id = ann["classId"]
                if old_id in classid_conversion:
                    new_id = classid_conversion[old_id]
                    ann["classId"] = new_id
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
                    from_s3_bucket, folder_path + '/' + mask_filename
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
    project, folder_path, classid_conversion=None, from_s3_bucket=None
):
    """Finds and uploads all JSON files in the folder_path as pre-annotations to the project.

    :param project: metadata of the project to upload pre-annotations to
    :type project: dict
    :param folder_path: from which folder to upload the pre-annotations
    :type folder_path: Pathlike (str or Path)
    :param classid_conversion: if not None, then class ID-es of the annotations
                               will be translated according to this dict during
                               the upload. This dict can be got when uploading
                               classes.json with create_annotation_classes_from_classes_json
    :type classid_conversion: dict
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str

    :return: paths to pre-annotations uploaded
    :rtype: list of strs
    """
    team_id, project_id, project_type = project["team_id"], project[
        "id"], project["type"]
    logger.info(
        "Uploading all preannotations from %s to project ID %s.", folder_path,
        project_id
    )
    if project_type == 2:
        raise SABaseException(
            406, '{"error":"This feature is only for vector projects."}'
        )
    if from_s3_bucket is None:
        preannotations_paths = list(Path(folder_path).glob('*.json'))
        preannotations_filenames = [x.name for x in preannotations_paths]
    else:
        s3_client = boto3.client('s3')
        paginator = s3_client.get_paginator('list_objects_v2')
        response_iterator = paginator.paginate(
            Bucket=from_s3_bucket, Prefix=folder_path
        )

        preannotations_paths = []
        for response in response_iterator:
            for object_data in response['Contents']:
                key = object_data['Key']
                if '/' in key[len(folder_path) + 1:]:
                    continue
                if key.endswith('.json'):
                    preannotations_paths.append(key)
        preannotations_filenames = [Path(x).name for x in preannotations_paths]

    len_preannotations_paths = len(preannotations_paths)
    logger.info(
        "Uploading %s preannotations to project ID %s.",
        len_preannotations_paths, project_id
    )
    if len_preannotations_paths == 0:
        return
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
                    folder_path, classid_conversion, thread_id, chunksize,
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
    return [str(p) for p in preannotations_paths]


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
    project, accessKeyId, secretAccessKey, bucket_name, folder_path
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
    """
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
