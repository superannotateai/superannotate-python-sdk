import math
from tqdm import tqdm
import threading
import io
import time
from pathlib import Path
from .. import common
import logging
import uuid
from PIL import Image, ImageOps
import json
from ..api import API
from ..exceptions import SABaseException, SAImageSizeTooLarge, SANonExistingProjectNameException
import datetime
import boto3
from .project_api import get_project_metadata_bare

_api = API.get_instance()
logger = logging.getLogger("superannotate-python-sdk")


# Yield successive n-sized
# chunks from l.
def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_project_folder_string(project):
    if isinstance(project, dict):
        return project['name']
    elif isinstance(project, tuple):
        project, folder = project
        project_name = project['name']
        if folder:
            return project_name + '/' + folder['name']
        return project_name
    elif isinstance(project, str):
        return project


def __move_images(
        source_project, source_folder_id, destination_folder_id, image_names
):
    """Move images in bulk between folders in a project 

    :param source_project: source project
    :type source_project: dict
    :param source_folder_id: source folder id
    :type source_folder_id: int
    :param image_names: image names. If None, all images from source project will be moved
    :type image: list of str
    :param destination_folder_id: destination folder id
    :type destination_folder_id: int
    :return: tuple of moved images list and skipped images list
    :rtype: tuple of lists
    """

    image_names_lists = divide_chunks(image_names, 1000)
    total_skipped = []
    total_moved = []
    logs = []

    for image_names in image_names_lists:
        response = _api.send_request(
            req_type='POST',
            path='/image/move',
            params={
                "team_id": source_project["team_id"],
                "project_id": source_project["id"]
            },
            json_req={
                "image_names": image_names,
                "destination_folder_id": destination_folder_id,
                "source_folder_id": source_folder_id
            }
        )

        if not response.ok:
            logs.append("Couldn't move images " + response.text)
            total_skipped += image_names
            continue
        res = response.json()
        total_moved += res['done']

    total_skipped = list(set(image_names) - set(total_moved))
    return (total_moved, total_skipped, logs)


def _copy_images_request(
        team_id, project_id, image_names, destination_folder_id, source_folder_id,
        include_annotations, copy_pin
):
    response = _api.send_request(
        req_type='POST',
        path='/images/copy-image-or-folders',
        params={
            "team_id": team_id,
            "project_id": project_id
        },
        json_req={
            "is_folder_copy": False,
            "image_names": image_names,
            "destination_folder_id": destination_folder_id,
            "source_folder_id": source_folder_id,
            "include_annotations": include_annotations,
            "keep_pin_status": copy_pin
        }
    )
    return response


def copy_polling(image_names, source_project, poll_id):
    done_count = 0
    skipped_count = 0
    now_timestamp = datetime.datetime.now().timestamp()
    delta_seconds = len(image_names) * 0.3
    max_timestamp = now_timestamp + delta_seconds
    logs = []
    while True:
        now_timestamp = datetime.datetime.now().timestamp()
        if (now_timestamp > max_timestamp):
            break
        response = _api.send_request(
            req_type='GET',
            path='/images/copy-image-progress',
            params={
                "team_id": source_project["team_id"],
                "project_id": source_project["id"],
                "poll_id": poll_id
            }
        )
        if not response.ok:
            logs.append("Couldn't copy images " + response.text)
            continue
        res = response.json()
        done_count = int(res['done'])
        skipped_count = int(res['skipped'])
        total_count = int(res['total_count'])
        if (skipped_count + done_count == total_count):
            break
        time.sleep(4)
    response = _api.send_request(
        req_type='GET',
        path='/images/copy-image-progress',
        params={
            "team_id": source_project["team_id"],
            "project_id": source_project["id"],
            "poll_id": poll_id
        }
    )
    if not response.ok:
        logs.append("Couldn't copy images " + response.text)
    else:
        res = response.json()
        done_count = int(res['done'])
        skipped_count = int(res['skipped'])
    return (skipped_count, done_count, logs)


def __copy_images(
        source_project, source_folder_id, destination_folder_id, image_names,
        include_annotations, copy_pin
):
    """Copy images in bulk between folders in a project 

    :param source_project: source project
    :type source_project: dict
    :param source_folder_id: source folder id
    :type source_folder_id: int
    :param image_names: image names. If None, all images from source project will be moved
    :type image: list of str
    :param destination_folder_id: destination folder id
    :type destination_folder_id: int
    :param include_annotations: enables annotations copy
    :type include_annotations: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    """

    team_id = source_project["team_id"]
    project_id = source_project["id"]

    image_names_lists = divide_chunks(image_names, 1000)
    total_skipped_count = 0
    total_done_count = 0
    total_skipped_list = []

    logs = []

    for image_names in image_names_lists:
        duplicates = get_duplicate_image_names(
            project_id=project_id,
            team_id=team_id,
            folder_id=destination_folder_id,
            image_paths=image_names
        )
        total_skipped_list += duplicates
        image_names = list(set(image_names) - set(duplicates))
        if not image_names:
            continue

        response = _copy_images_request(
            team_id, project_id, image_names, destination_folder_id,
            source_folder_id, include_annotations, copy_pin
        )
        if not response.ok:
            logs.append("Couldn't copy images " + response.text)
            total_skipped_list += image_names
            continue

        res = response.json()
        poll_id = res['poll_id']
        skipped_count, done_count, polling_logs = copy_polling(
            image_names, source_project, poll_id
        )
        logs += polling_logs
        total_skipped_count += skipped_count
        total_done_count += done_count
    return (total_done_count, total_skipped_list, logs)


def create_empty_annotation(size, image_name):
    return {
        "metadata": {
            'height': size[1],
            'width': size[0],
            'name': image_name
        }
    }


def upload_image_array_to_s3(
        bucket, img_name, img_name_hash, size, orig_image, lores_image, huge_image,
        thumbnail_image, prefix
):
    key = prefix + img_name_hash
    bucket.put_object(Body=orig_image, Key=key)
    bucket.put_object(Body=lores_image, Key=key + '___lores.jpg')
    bucket.put_object(
        Body=huge_image,
        Key=key + '___huge.jpg',
        Metadata={
            'height': str(size[1]),
            'width': str(size[0])
        }
    )
    bucket.put_object(Body=thumbnail_image, Key=key + '___thumb.jpg')
    bucket.put_object(
        Body=json.dumps(create_empty_annotation(size, img_name)),
        Key=key + ".json"
    )
    return key


def get_image_array_to_upload(
        img_name, byte_io_orig, image_quality_in_editor, project_type
):
    if image_quality_in_editor not in ["original", "compressed"]:
        raise SABaseException(0, "NA ImageQuality in get_image_array_to_upload")
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(byte_io_orig)
    im_format = im.format

    im = ImageOps.exif_transpose(im)

    width, height = im.size

    resolution = width * height
    if resolution > common.MAX_IMAGE_RESOLUTION[project_type]:
        raise SABaseException(
            0, "Image resolution " + str(resolution) +
               " too large. Max supported for " + project_type + " projects is " +
               str(common.MAX_IMAGE_RESOLUTION[project_type])
        )

    if image_quality_in_editor == "original" and im_format in ['JPEG', 'JPG']:
        byte_io_lores = io.BytesIO(byte_io_orig.getbuffer())
    else:
        byte_io_lores = io.BytesIO()
        bg = Image.new('RGBA', im.size, (255, 255, 255))
        im = im.convert("RGBA")
        bg.paste(im, mask=im)
        bg = bg.convert('RGB')
        if image_quality_in_editor == "original":
            bg.save(byte_io_lores, 'JPEG', quality=100, subsampling=0)
        else:
            bg.save(byte_io_lores, 'JPEG', quality=60)
        im = bg

    byte_io_huge = io.BytesIO()
    hsize = int(height * 600.0 / width)
    im.resize((600, hsize), Image.ANTIALIAS).save(byte_io_huge, 'JPEG')

    byte_io_thumbs = io.BytesIO()
    thumbnail_size = (128, 96)
    background = Image.new('RGB', thumbnail_size, "black")
    im.thumbnail(thumbnail_size, Image.ANTIALIAS)
    (w, h) = im.size
    background.paste(
        im, ((thumbnail_size[0] - w) // 2, (thumbnail_size[1] - h) // 2)
    )
    im = background
    im.save(byte_io_thumbs, 'JPEG')

    byte_io_thumbs.seek(0)
    byte_io_lores.seek(0)
    byte_io_huge.seek(0)
    byte_io_orig.seek(0)

    img_name_hash = str(uuid.uuid4()) + Path(img_name).suffix
    return img_name, img_name_hash, (
        width, height
    ), byte_io_orig, byte_io_lores, byte_io_huge, byte_io_thumbs


def __upload_images_to_aws_thread(
        res, img_paths, project, annotation_status, prefix, thread_id, chunksize,
        couldnt_upload, uploaded, tried_upload, image_quality_in_editor,
        from_s3_bucket, project_folder_id
):
    len_img_paths = len(img_paths)
    start_index = thread_id * chunksize
    end_index = start_index + chunksize
    if from_s3_bucket is not None:
        from_session = boto3.Session()
        from_s3 = from_session.resource('s3')
    if start_index >= len_img_paths:
        return
    s3_session = _get_boto_session_by_credentials(res)
    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(res["bucket"])
    prefix = res['filePath']
    uploaded_imgs = []
    uploaded_imgs_info = ([], [], [])
    for i in range(start_index, end_index):
        if i >= len_img_paths:
            break
        path = img_paths[i]
        tried_upload[thread_id].append(path)
        try:
            if from_s3_bucket is not None:
                file = io.BytesIO()
                from_s3_object = from_s3.Object(from_s3_bucket, path)
                file_size = from_s3_object.content_length
                if file_size > common.MAX_IMAGE_SIZE:
                    raise SAImageSizeTooLarge(file_size)
                from_s3_object.download_fileobj(file)
            else:
                file_size = Path(path).stat().st_size
                if file_size > common.MAX_IMAGE_SIZE:
                    raise SAImageSizeTooLarge(file_size)
                with open(path, "rb") as f:
                    file = io.BytesIO(f.read())
            images_array = get_image_array_to_upload(
                Path(path).name, file, image_quality_in_editor, project["type"]
            )
            key = upload_image_array_to_s3(bucket, *images_array, prefix)
        except Exception as e:
            logger.warning("Unable to upload image %s. %s", path, e)
            couldnt_upload[thread_id].append(path)
            continue
        else:
            uploaded_imgs.append(path)
            uploaded_imgs_info[0].append(Path(path).name)
            uploaded_imgs_info[1].append(key)
            uploaded_imgs_info[2].append(images_array[2])
            if len(uploaded_imgs) >= 100:
                try:
                    __create_image(
                        uploaded_imgs_info[0],
                        uploaded_imgs_info[1],
                        project,
                        annotation_status,
                        prefix,
                        uploaded_imgs_info[2],
                        project_folder_id,
                        upload_state="Basic"
                    )
                except SABaseException as e:
                    couldnt_upload[thread_id] += uploaded_imgs
                    logger.warning(e)
                else:
                    uploaded[thread_id] += uploaded_imgs
                uploaded_imgs = []
                uploaded_imgs_info = ([], [], [])
    try:
        __create_image(
            uploaded_imgs_info[0],
            uploaded_imgs_info[1],
            project,
            annotation_status,
            prefix,
            uploaded_imgs_info[2],
            project_folder_id,
            upload_state="Basic"
        )
    except SABaseException as e:
        couldnt_upload[thread_id] += uploaded_imgs
        logger.warning(e)
    else:
        uploaded[thread_id] += uploaded_imgs


def __create_image(
        img_names,
        img_paths,
        project,
        annotation_status,
        remote_dir,
        sizes,
        project_folder_id,
        upload_state="Initial"
):
    if len(img_paths) == 0:
        return
    team_id, project_id = project["team_id"], project["id"]
    upload_state_code = common.upload_state_str_to_int(upload_state)
    data = {
        "project_id": str(project_id),
        "team_id": str(team_id),
        "images": [],
        "annotation_status": annotation_status,
        "meta": {},
        "upload_state": upload_state_code
    }
    if project_folder_id is not None:
        data["folder_id"] = project_folder_id
    for img_data, img_path, size in zip(img_names, img_paths, sizes):
        img_name_uuid = Path(img_path).name
        remote_path = remote_dir + f"{img_name_uuid}"
        if upload_state == "External":
            img_name, img_url = img_data
        else:
            img_name, img_url = img_data, remote_path
        data["images"].append({"name": img_name, "path": img_url})
        data["meta"][img_name] = {
            "width": size[0],
            "height": size[1],
            "annotation_json_path": remote_path + ".json",
            "annotation_bluemap_path": remote_path + ".png"
        }

    response = _api.send_request(
        req_type='POST', path='/image/ext-create', json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't ext-create image " + response.text
        )


def _get_upload_auth_token(params, project_id):
    response = _api.send_request(
        req_type='GET',
        path=f'/project/{project_id}/sdkImageUploadToken',
        params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get upload token " + response.text
        )

    res = response.json()
    return res


def _get_boto_session_by_credentials(credentials):
    return boto3.Session(
        aws_access_key_id=credentials['accessKeyId'],
        aws_secret_access_key=credentials['secretAccessKey'],
        aws_session_token=credentials['sessionToken'],
        region_name=credentials['region']
    )


def __tqdm_thread_image_upload(total_num, tried_upload, finish_event):
    _TIME_TO_UPDATE_IN_TQDM = 1
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(_TIME_TO_UPDATE_IN_TQDM)
            if not finished:
                sum_all = 0
                for i in tried_upload:
                    sum_all += len(i)
                pbar.update(sum_all - pbar.n)
            else:
                pbar.update(total_num - pbar.n)
                break


def get_duplicate_image_names(project_id, team_id, folder_id, image_paths):
    """ Find duplicated images in a folder.
    :param project_id: project_id
    :type project_id: int
    :param team_id: team_id
    :type team_id: int
    :param folder_id: folder_id
    :type folder_id: int
    :param image_paths: list
    :type image_paths: list of str

    :return: list of duplicated images
    :rtype: list of strs
    """
    duplicate_images = []
    image_paths_lists = divide_chunks(image_paths, 500)
    for image_path_list in image_paths_lists:
        json_req = {
            'project_id': project_id,
            'team_id': team_id,
            'folder_id': folder_id
        }
        image_list = [Path(image_path).name for image_path in image_path_list]
        json_req['names'] = image_list
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
        duplicate_images += response.json()
    duplicate_images_names = [i['name'] for i in duplicate_images]
    return duplicate_images_names


def _upload_images(
        img_paths, team_id, folder_id, project_id, annotation_status,
        from_s3_bucket, image_quality_in_editor, project, folder_name
):
    _NUM_THREADS = 10
    uploaded = [[] for _ in range(_NUM_THREADS)]
    tried_upload = [[] for _ in range(_NUM_THREADS)]
    couldnt_upload = [[] for _ in range(_NUM_THREADS)]
    finish_event = threading.Event()
    params = {'team_id': team_id, 'folder_id': folder_id}
    res = _get_upload_auth_token(params=params, project_id=project_id)

    prefix = res['filePath']
    limit = res['availableImageCount']
    imgs_to_upload = img_paths[:limit]
    duplicate_images_names = get_duplicate_image_names(
        project_id=project_id,
        team_id=team_id,
        folder_id=folder_id,
        image_paths=imgs_to_upload
    )

    if len(duplicate_images_names):
        logger.warning(
            "%s already existing images found that won't be uploaded.",
            len(duplicate_images_names)
        )
    imgs_to_upload = [
        i for i in imgs_to_upload if Path(i).name not in duplicate_images_names
    ]
    logger.info(
        "Uploading %s images to project %s.", len(imgs_to_upload), folder_name
    )

    images_to_skip = [str(path) for path in img_paths[limit:]]

    chunksize = int(math.ceil(len(imgs_to_upload) / _NUM_THREADS))

    tqdm_thread = threading.Thread(
        target=__tqdm_thread_image_upload,
        args=(len(imgs_to_upload), tried_upload, finish_event),
        daemon=True
    )
    tqdm_thread.start()

    threads = []
    for thread_id in range(_NUM_THREADS):
        t = threading.Thread(
            target=__upload_images_to_aws_thread,
            args=(
                res, imgs_to_upload, project, annotation_status, prefix,
                thread_id, chunksize, couldnt_upload, uploaded, tried_upload,
                image_quality_in_editor, from_s3_bucket, folder_id
            ),
            daemon=True
        )
        threads.append(t)
        t.start()
    for thread in threads:
        thread.join()
    finish_event.set()
    tqdm_thread.join()
    not_uploaded = [str(f) for s in couldnt_upload for f in s]
    uploaded = [str(f) for s in uploaded for f in s]
    not_uploaded += images_to_skip

    return (uploaded, not_uploaded, duplicate_images_names)


def _attach_urls(
        img_names_urls, team_id, folder_id, project_id, annotation_status, project,
        folder_name
):
    _NUM_THREADS = 10
    params = {'team_id': team_id, 'folder_id': folder_id}
    uploaded = [[] for _ in range(_NUM_THREADS)]
    tried_upload = [[] for _ in range(_NUM_THREADS)]
    couldnt_upload = [[] for _ in range(_NUM_THREADS)]
    finish_event = threading.Event()

    res = _get_upload_auth_token(params=params, project_id=project_id)

    prefix = res['filePath']
    limit = res['availableImageCount']
    images_to_upload = img_names_urls[:limit]

    img_names = [i[0] for i in images_to_upload]
    duplicate_images = get_duplicate_image_names(
        project_id=project_id,
        team_id=team_id,
        folder_id=folder_id,
        image_paths=img_names
    )
    if len(duplicate_images) != 0:
        logger.warning(
            "%s already existing images found that won't be uploaded.",
            len(duplicate_images)
        )

    images_to_upload = [
        i for i in images_to_upload if i[0] not in duplicate_images
    ]
    logger.info(
        "Uploading %s images to project %s.", len(images_to_upload), folder_name
    )

    images_to_skip = img_names_urls[limit:]
    chunksize = int(math.ceil(len(images_to_upload) / _NUM_THREADS))

    tqdm_thread = threading.Thread(
        target=__tqdm_thread_image_upload,
        args=(len(images_to_upload), tried_upload, finish_event),
        daemon=True
    )
    tqdm_thread.start()
    threads = []
    for thread_id in range(_NUM_THREADS):
        t = threading.Thread(
            target=__attach_image_urls_to_project_thread,
            args=(
                res, images_to_upload, project, annotation_status, prefix,
                thread_id, chunksize, couldnt_upload, uploaded, tried_upload,
                folder_id
            ),
            daemon=True
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    finish_event.set()
    tqdm_thread.join()
    list_of_not_uploaded = []
    for couldnt_upload_thread in couldnt_upload:
        for f in couldnt_upload_thread:
            list_of_not_uploaded.append(str(f))
    list_of_uploaded = []
    for upload_thread in uploaded:
        for f in upload_thread:
            list_of_uploaded.append(str(f))

    list_of_not_uploaded += [i[0] for i in images_to_skip]
    return (list_of_uploaded, list_of_not_uploaded, duplicate_images)


def __attach_image_urls_to_project_thread(
        res, img_names_urls, project, annotation_status, prefix, thread_id,
        chunksize, couldnt_upload, uploaded, tried_upload, project_folder_id
):
    len_img_paths = len(img_names_urls)
    start_index = thread_id * chunksize
    end_index = start_index + chunksize
    if start_index >= len_img_paths:
        return
    s3_session = _get_boto_session_by_credentials(res)
    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(res["bucket"])
    prefix = res['filePath']
    uploaded_imgs = []
    uploaded_imgs_info = ([], [], [])
    for i in range(start_index, end_index):
        if i >= len_img_paths:
            break
        name, _ = img_names_urls[i]
        tried_upload[thread_id].append(name)
        img_name_hash = str(uuid.uuid4()) + Path(name).suffix
        key = prefix + img_name_hash
        try:
            bucket.put_object(
                Body=json.dumps(create_empty_annotation((None, None), name)),
                Key=key + ".json"
            )
        except Exception as e:
            logger.warning("Unable to upload image %s. %s", name, e)
            couldnt_upload[thread_id].append(name)
            continue
        else:
            uploaded_imgs.append(name)
            uploaded_imgs_info[0].append(img_names_urls[i])
            uploaded_imgs_info[1].append(key)
            uploaded_imgs_info[2].append((None, None))
            if len(uploaded_imgs) >= 100:
                try:
                    __create_image(
                        uploaded_imgs_info[0],
                        uploaded_imgs_info[1],
                        project,
                        annotation_status,
                        prefix,
                        uploaded_imgs_info[2],
                        project_folder_id,
                        upload_state="External"
                    )
                except SABaseException as e:
                    couldnt_upload[thread_id] += uploaded_imgs
                    logger.warning(e)
                else:
                    uploaded[thread_id] += uploaded_imgs
                uploaded_imgs = []
                uploaded_imgs_info = ([], [], [])
    try:
        __create_image(
            uploaded_imgs_info[0],
            uploaded_imgs_info[1],
            project,
            annotation_status,
            prefix,
            uploaded_imgs_info[2],
            project_folder_id,
            upload_state="External"
        )
    except SABaseException as e:
        couldnt_upload[thread_id] += uploaded_imgs
        logger.warning(e)
    else:
        uploaded[thread_id] += uploaded_imgs


def get_templates_mapping():
    response = _api.send_request(
        req_type='GET', path=f'/templates', params={"team_id": _api.team_id}
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get templates " + response.text
        )
    res = response.json()
    templates = res['data']
    templates_map = {}
    for template in templates:
        templates_map[template['name']] = template['id']
    return templates_map


def _assign_images(folder_name, image_names, user, project_id, team_id):
    image_names_lists = divide_chunks(image_names, 500)
    params = {"project_id": project_id, "team_id": team_id}
    messages = []
    for image_name_list in image_names_lists:
        json_req = {
            "image_names": image_name_list,
            "assign_user_id": user,
            "folder_name": folder_name,
        }
        response = _api.send_request(
            req_type='PUT',
            path='/images/editAssignment',
            params=params,
            json_req=json_req
        )
        if not response.ok:
            message = "Couldn't assign images " + response.text
            messages.append(message)
    return messages


def _unassign_images(folder_name, image_names, project_id, team_id):
    image_names_lists = divide_chunks(image_names, 500)
    params = {"project_id": project_id, "team_id": team_id}
    messages = []
    for image_name_list in image_names_lists:
        json_req = {
            "image_names": image_name_list,
            "remove_user_ids": ["all"],
            "folder_name": folder_name,
        }
        response = _api.send_request(
            req_type='PUT',
            path='/images/editAssignment',
            params=params,
            json_req=json_req
        )
        if not response.ok:
            message = "Couldn't assign images " + response.text
            messages.append(message)
    return messages



