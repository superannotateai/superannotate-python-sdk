import math
import time
import logging
import threading
from pathlib import Path
import io
import json

import boto3
from tqdm import tqdm
from PIL import Image

from ..api import API
from ..exceptions import SABaseException

logger = logging.getLogger("annotateonline-python-sdk")

_api = API.get_instance()
_NUM_THREADS = 10

_RESIZE_CONFIG = {2: 4000000, 1: 100000000}  # 1: vector 2: pixel


def search_projects(team, name_prefix=None):
    """Search for name_prefix prefixed projects in the team.
    Returns
    -------
    list of Project
    """
    result_list = []
    params = {'team_id': str(team['id']), 'offset': 0}
    if name_prefix is not None:
        params['name'] = name_prefix
    while True:
        response = _api.gen_request(
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


def get_project(project):
    """Returns the project with project_id in the team.
    Returns
    -------
    Project
    """
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': str(team_id)}
    response = _api.gen_request(
        req_type='GET', path=f'/project/{project_id}', params=params
    )
    if response.ok:
        res = response.json()
        return res
    else:
        raise SABaseException(
            response.status_code, "Couldn't get project." + response.text
        )


def create_project(team, project_name, project_description, project_type):
    """Creates a new project in the team.
    if project_type is 1 vector and 2 for pixel project
    Returns
    -------
    dict:
        the created project representation
    """
    if project_type not in [1, 2]:
        raise SABaseException(
            0, "project_type should be 1 (vector) or 2 (pixel)"
        )
    data = {
        "team_id": str(team['id']),
        "name": project_name,
        "description": project_description,
        "status": 0,
        "type": project_type
    }
    response = _api.gen_request(req_type='POST', path='/project', json_req=data)
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't create project " + response.text
        )
    res = response.json()
    logger.info(
        "Created project %s (ID %s) with type %s", res["name"], res["id"],
        res["type"]
    )
    return res


def delete_project(project):
    """Deletes project from the team
    Returns
    -------
    None
    """
    team_id, project_id = project["team_id"], project["id"]
    params = {"team_id": team_id}
    response = _api.gen_request(
        req_type='DELETE', path=f'/project/{project_id}', params=params
    )
    if response.ok:
        logger.info("Successfully deleted project with ID %s.", project_id)
    else:
        raise SABaseException(
            response.status_code, "Couldn't delete project " + response.text
        )


def get_project_image_count(project):
    """Get total image count of the project
    Returns
    -------
    int
        Number of images
    """
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': team_id}
    response = _api.gen_request(
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


def get_project_type(project):
    """Get type of project
    Returns
    -------
    int
        1 = vector
        2 = pixel
    """
    return get_project(project)["type"]


def upload_images_from_folder(
    project,
    folder_path,
    extensions=None,
    annotation_status=1,
    from_s3_bucket=None,
    exclude_file_pattern="___save.png"
):
    """Uploads all images with extension from folder_path to the project.
    Sets status of all the uploaded images to set_status if it is not None.
    Returns
    -------
    None
    """
    project_id = project["id"]
    if extensions is None:
        extensions = ["jpg", "png"]
    elif not isinstance(extensions, list):
        raise SABaseException(
            0, "extensions should be a list in upload_images_from_folder"
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
    upload_images(project, filtered_paths, annotation_status, from_s3_bucket)


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
        try:
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
            bucket.put_object(Body=byte_io, Key=key, ContentType="image/jpeg")
            byte_io = io.BytesIO()
            im.convert('RGB').save(byte_io, 'JPEG', dpi=(96, 96))
            byte_io.seek(0)
            bucket.put_object(
                Body=byte_io,
                Key=key + '___lores.jpg',
                ContentType="image/jpeg"
            )
            byte_io = io.BytesIO()
            im.convert('RGB').resize((128, 96)
                                    ).save(byte_io, 'JPEG', dpi=(96, 96))
            byte_io.seek(0)
            bucket.put_object(
                Body=byte_io,
                Key=key + '___thumb.jpg',
                ContentType="image/jpeg"
            )
        except Exception as e:
            logger.warning("Unable to upload to data server %s", e)
            break
        else:
            num_uploaded[thread_id] += 1
            already_uploaded[i] = True
            uploaded_imgs.append(path)
            if len(uploaded_imgs) >= 100:
                __create_image(
                    uploaded_imgs, project, annotation_status, prefix
                )
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

    response = _api.gen_request(
        req_type='POST', path='/image/ext-create', json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't ext-create image " + response.text
        )


def upload_images(project, img_paths, annotation_status=1, from_s3_bucket=None):
    """Uploads all images given in list of path objects in img_paths to the project.
    Sets status of all the uploaded images to set_status if it is not None.
    annotation_status = {
    1: "notStarted",
    2: "annotation",
    3: "qualityCheck",
    4: "issueFix",
    5: "complete",
    6: "skipped"
    Returns
    -------
    None
    """
    if annotation_status not in [1, 2, 3, 4, 5, 6]:
        raise SABaseException(
            0, "Annotation status should be an integer in range 1-6"
        )
    project_type = get_project_type(project)
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
        response = _api.gen_request(
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


def __upload_annotations_thread(
    team_id, project_id, project_type, anns_filenames, folder_path,
    old_to_new_classes_conversion, thread_id, chunksize, num_uploaded,
    from_s3_bucket
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
        response = _api.gen_request(
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

            if old_to_new_classes_conversion is not None:
                for ann in annotation_json:
                    if 'classId' not in ann:
                        continue
                    if ann['classId'] == -1:
                        continue
                    old_id = ann["classId"]
                    if old_id in old_to_new_classes_conversion:
                        new_id = old_to_new_classes_conversion[old_id]
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


def upload_annotations_from_folder(
    project,
    folder_path,
    old_to_new_classes_conversion=None,
    from_s3_bucket=None
):
    """Uploads all annotations given in list of path objects in annotations_paths to the project.
    If classes_json_path is given
    Returns
    -------
    None
    """
    project_type = get_project_type(project)
    team_id, project_id = project["team_id"], project["id"]
    logger.info(
        "Uploading all annotations from %s to project ID %s.", folder_path,
        project_id
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
                folder_path, old_to_new_classes_conversion, thread_id,
                chunksize, num_uploaded, from_s3_bucket
            )
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    finish_event.set()
    tqdm_thread.join()
    logger.info("Number of annotations uploaded %s.", sum(num_uploaded))


def __upload_preannotations_thread(
    aws_creds, project_type, preannotations_filenames, folder_path,
    old_to_new_classes_conversion, thread_id, chunksize, num_uploaded,
    already_uploaded, from_s3_bucket
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

        if old_to_new_classes_conversion is not None:
            for ann in annotation_json:
                if 'classId' not in ann:
                    continue
                if ann['classId'] == -1:
                    continue
                old_id = ann["classId"]
                if old_id in old_to_new_classes_conversion:
                    new_id = old_to_new_classes_conversion[old_id]
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


def get_root_folder_id(project):
    """Get root folder ID
    Returns
    -------
    int
        Root folder ID
    """
    params = {'team_id': project['team_id']}
    response = _api.gen_request(
        req_type='GET', path=f'/project/{project["id"]}', params=params
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    return response.json()['folder_id']


def upload_preannotations_from_folder(
    project,
    folder_path,
    old_to_new_classes_conversion=None,
    from_s3_bucket=None
):
    """Uploads all annotations given in list of path objects in annotations_paths to the project.
    If classes_json_path is given
    Returns
    -------
    None
    """
    team_id, project_id = project["team_id"], project["id"]
    project_type = get_project_type(project)
    logger.info(
        "Uploading all preannotations from %s to project ID %s.", folder_path,
        project_id
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
        response = _api.gen_request(
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
                    folder_path, old_to_new_classes_conversion, thread_id,
                    chunksize, num_uploaded, already_uploaded, from_s3_bucket
                )
            )
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    finish_event.set()
    tqdm_thread.join()
    logger.info("Number of preannotations uploaded %s.", sum(num_uploaded))


def share_project(project, user, user_role):
    """    2: "Admin",
    3: "Annotator",
    4: "QA",
    5: "Customer",
    6: "Viewer
    """
    team_id, project_id = project["team_id"], project["id"]
    user_id = user["id"]
    json_req = {"user_id": user_id, "user_role": user_role}
    params = {'team_id': team_id}
    response = _api.gen_request(
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
    team_id, project_id = project["team_id"], project["id"]
    user_id = user["id"]
    json_req = {"user_id": user_id}
    params = {'team_id': team_id}
    response = _api.gen_request(
        req_type='DELETE',
        path=f'/project/{project_id}/share',
        params=params,
        json_req=json_req
    )
    if not response.ok:
        raise SABaseException(response.status_code, response.text)
    logger.info("Unshared project ID %s from user ID %s", project_id, user_id)


def upload_from_s3_bucket(
    project, accessKeyId, secretAccessKey, bucket_name, folder_name
):
    team_id, project_id = project["team_id"], project["id"]
    params = {
        "team_id": team_id,
    }
    data = {
        "accessKeyID": accessKeyId,
        "secretAccessKey": secretAccessKey,
        "bucketName": bucket_name,
        "folderName": folder_name
    }
    response = _api.gen_request(
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
        res = get_upload_from_s3_bucket_status(project)
        if res["progress"] == '2':
            break
        if res["progress"] != "1":
            raise SABaseException(
                response.status_code,
                "Couldn't upload to project from S3 " + response.text
            )


def get_upload_from_s3_bucket_status(project):
    team_id, project_id = project["team_id"], project["id"]
    params = {
        "team_id": team_id,
    }
    response = _api.gen_request(
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
