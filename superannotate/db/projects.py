import cgi
import copy
import io
import json
import logging
import math
import os
import random
import tempfile
import threading
import time
from os.path import basename
from pathlib import Path
from urllib.parse import urlparse

import boto3
import cv2
import ffmpeg
import requests
from azure.storage.blob import BlobServiceClient
from google.cloud import storage
from PIL import Image, ImageOps
from tqdm import tqdm

from .. import common
from ..api import API
from ..exceptions import (
    SABaseException, SAExistingProjectNameException, SAImageSizeTooLarge,
    SANonExistingProjectNameException
)
from .annotation_classes import (
    check_annotation_json, create_annotation_classes_from_classes_json,
    fill_class_and_attribute_ids, get_annotation_classes_name_to_id,
    search_annotation_classes
)
from .images import search_images
from .project_api import get_project_metadata_bare
from .users import get_team_contributor_metadata

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()
_NUM_THREADS = 10


def create_project(project_name, project_description, project_type):
    """Create a new project in the team.

    :param project_name: the new project's name
    :type project_name: str
    :param project_description: the new project's description
    :type project_description: str
    :param project_type: the new project type, Vector or Pixel.
    :type project_type: str

    :return: dict object metadata the new project
    :rtype: dict
    """
    try:
        get_project_metadata_bare(project_name)
    except SANonExistingProjectNameException:
        pass
    else:
        raise SAExistingProjectNameException(
            0, "Project with name " + project_name +
            " already exists. Please use unique names for projects to use with SDK."
        )
    project_type = common.project_type_str_to_int(project_type)
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
        common.project_type_int_to_str(res["type"])
    )
    res["type"] = common.project_type_int_to_str(res["type"])
    return res


def create_project_from_metadata(project_metadata):
    """Create a new project in the team using project metadata object dict.
    Mandatory keys in project_metadata are "name", "description" and "type" (Vector or Pixel)
    Non-mandatory keys: "workflow", "contributors", "settings" and "annotation_classes".

    :return: dict object metadata the new project
    :rtype: dict
    """
    new_project_metadata = create_project(
        project_metadata["name"], project_metadata["description"],
        project_metadata["type"]
    )
    if "contributors" in project_metadata:
        for user in project_metadata["contributors"]:
            share_project(
                new_project_metadata, user["user_id"], user["user_role"]
            )
    if "settings" in project_metadata:
        set_project_settings(new_project_metadata, project_metadata["settings"])
    if "annotation_classes" in project_metadata:
        create_annotation_classes_from_classes_json(
            new_project_metadata, project_metadata["annotation_classes"]
        )
    if "workflow" in project_metadata:
        set_project_workflow(new_project_metadata, project_metadata["workflow"])
    return new_project_metadata


def delete_project(project):
    """Deletes the project

    :param project: project name or metadata of the project to be deleted
    :type project: str or dict
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    team_id, project_id = project["team_id"], project["id"]
    params = {"team_id": team_id}
    response = _api.send_request(
        req_type='DELETE', path=f'/project/{project_id}', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't delete project " + response.text
        )
    logger.info("Successfully deleted project %s.", project["name"])


def rename_project(project, new_name):
    """Renames the project

    :param project: project name or metadata of the project to be deleted
    :type project: str or dict
    :param new_name: project's new name
    :type new_name: str
    """
    try:
        get_project_metadata_bare(new_name)
    except SANonExistingProjectNameException:
        pass
    else:
        raise SAExistingProjectNameException(
            0, "Project with name " + new_name +
            " already exists. Please use unique names for projects to use with SDK."
        )
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    team_id, project_id = project["team_id"], project["id"]
    params = {"team_id": team_id}
    json_req = {"name": new_name}
    response = _api.send_request(
        req_type='PUT',
        path=f'/project/{project_id}',
        params=params,
        json_req=json_req
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't rename project " + response.text
        )
    logger.info(
        "Successfully renamed project %s to %s.", project["name"], new_name
    )


def get_project_image_count(project):
    """Returns number of images in the project.

    :param project: project name or metadata of the project
    :type project: str or dict

    :return: number of images in the project
    :rtype: int
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
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


def upload_video_to_project(
    project,
    video_path,
    target_fps=None,
    start_time=0.0,
    end_time=None,
    annotation_status="NotStarted",
    image_quality_in_editor=None
):
    """Uploads image frames from video to platform. Uploaded images will have
    names "<video_name>_<frame_no>.jpg".

    :param project: project name or metadata of the project to upload video frames to
    :type project: str or dict
    :param video_path: video to upload
    :type video_path: Pathlike (str or Path)
    :param target_fps: how many frames per second need to extract from the video (approximate).
                       If None, all frames will be uploaded
    :type target_fps: float
    :param start_time: Time (in seconds) from which to start extracting frames
    :type start_time: float
    :param end_time: Time (in seconds) up to which to extract frames. If None up to end
    :type end_time: float
    :param annotation_status: value to set the annotation statuses of the uploaded
                              video frames NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: filenames of uploaded images
    :rtype: list of strs
    """
    logger.info("Uploading from video %s.", str(video_path))
    rotate_code = None
    try:
        meta_dict = ffmpeg.probe(str(video_path))
        rot = int(meta_dict['streams'][0]['tags']['rotate'])
        if rot == 90:
            rotate_code = cv2.ROTATE_90_CLOCKWISE
        elif rot == 180:
            rotate_code = cv2.ROTATE_180
        elif rot == 270:
            rotate_code = cv2.ROTATE_90_COUNTERCLOCKWISE
        if rot != 0:
            logger.info(
                "Frame rotation of %s found. Output images will be rotated accordingly.",
                rot
            )
    except Exception as e:
        logger.warning("Couldn't read video metadata %s", e)

    video = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    if not video.isOpened():
        raise SABaseException(0, "Couldn't open video file " + str(video_path))

    total_num_of_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_num_of_frames < 0:
        total_num_of_frames = 0
        flag = True
        while flag:
            flag, frame = video.read()
            if flag:
                total_num_of_frames += 1
            else:
                break
        video = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    logger.info("Video frame count is %s.", total_num_of_frames)

    if target_fps is not None:
        video_fps = float(video.get(cv2.CAP_PROP_FPS))
        logger.info(
            "Video frame rate is %s. Target frame rate is %s.", video_fps,
            target_fps
        )
        if target_fps >= video_fps:
            target_fps = None
        else:
            r = video_fps / target_fps
            percent_to_drop = 1.0 - 1.0 / r
            my_random = random.Random(122222)

    zero_fill_count = len(str(total_num_of_frames))
    tempdir = tempfile.TemporaryDirectory()

    video_name = Path(video_path).stem
    frame_no = 1
    logger.info("Extracting frames from video to %s.", tempdir.name)
    while True:
        success, frame = video.read()
        if not success:
            break
        if target_fps is not None and my_random.random() < percent_to_drop:
            continue
        frame_time = video.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if frame_time < start_time:
            continue
        if end_time is not None and frame_time > end_time:
            continue
        if rotate_code is not None:
            frame = cv2.rotate(frame, rotate_code)
        cv2.imwrite(
            str(
                Path(tempdir.name) / (
                    video_name + "_" + str(frame_no).zfill(zero_fill_count) +
                    ".jpg"
                )
            ), frame
        )
        frame_no += 1

    logger.info(
        "Extracted %s frames from video. Now uploading to platform.",
        frame_no - 1
    )

    filenames = upload_images_from_folder_to_project(
        project,
        tempdir.name,
        extensions=["jpg"],
        annotation_status=annotation_status,
        image_quality_in_editor=image_quality_in_editor
    )

    assert len(filenames[1]) == 0

    filenames_base = []
    for file in filenames[0]:
        filenames_base.append(Path(file).name)

    return filenames_base


def upload_videos_from_folder_to_project(
    project,
    folder_path,
    extensions=None,
    exclude_file_patterns=None,
    recursive_subfolders=False,
    target_fps=None,
    start_time=0.0,
    end_time=None,
    annotation_status="NotStarted",
    image_quality_in_editor=None
):
    """Uploads image frames from all videos with given extensions from folder_path to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: project name or metadata of the project to upload videos to
    :type project: str or dict
    :param folder_path: from which folder to upload the videos
    :type folder_path: Pathlike (str or Path)
    :param extensions: list of filename extensions to include from folder, if None, then
                       extensions = ["mp4", "avi", "mov", "webm", "flv", "mpg", "ogg"]
    :type extensions: list of str
    :param exclude_file_patterns: filename patterns to exclude from uploading
    :type exclude_file_patterns: list of strs
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool
    :param target_fps: how many frames per second need to extract from the video (approximate).
                       If None, all frames will be uploaded
    :type target_fps: float
    :param start_time: Time (in seconds) from which to start extracting frames
    :type start_time: float
    :param end_time: Time (in seconds) up to which to extract frames. If None up to end
    :type end_time: float
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded and not-uploaded video frame images' filenames
    :rtype: tuple of list of strs
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    if recursive_subfolders:
        logger.warning(
            "When using recursive subfolder parsing same name videos in different subfolders will overwrite each other."
        )
    if exclude_file_patterns is None:
        exclude_file_patterns = []
    if extensions is None:
        extensions = ["mp4", "avi", "mov", "webm", "flv", "mpg", "ogg"]
    elif not isinstance(extensions, list):
        raise SABaseException(
            0,
            "extensions should be a list in upload_images_from_folder_to_project"
        )

    logger.info(
        "Uploading all videos with extensions %s from %s to project %s. Excluded file patterns are: %s.",
        extensions, folder_path, project["name"], exclude_file_patterns
    )
    paths = []
    for extension in extensions:
        if not recursive_subfolders:
            paths += list(Path(folder_path).glob(f'*.{extension.lower()}'))
            if os.name != "nt":
                paths += list(Path(folder_path).glob(f'*.{extension.upper()}'))
        else:
            paths += list(Path(folder_path).rglob(f'*.{extension.lower()}'))
            if os.name != "nt":
                paths += list(Path(folder_path).rglob(f'*.{extension.upper()}'))
    filtered_paths = []
    for path in paths:
        not_in_exclude_list = [
            x not in Path(path).name for x in exclude_file_patterns
        ]
        if all(not_in_exclude_list):
            filtered_paths.append(path)

    filenames = []
    for path in filtered_paths:
        filenames += upload_video_to_project(
            project,
            path,
            target_fps=target_fps,
            start_time=start_time,
            end_time=end_time,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor
        )

    return filenames


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

    If an image with existing name already exists in the project it won't be uploaded,
    and its path will be appended to the third member of return value of this
    function.

    :param project: project name or metadata of the project to upload images_to
    :type project: str or dict
    :param folder_path: from which folder to upload the images
    :type folder_path: Pathlike (str or Path)
    :param extensions: list of filename extensions to include from folder, if None, then "jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp" are included
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
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded, could-not-upload, existing-images filepaths
    :rtype: tuple (3 members) of list of strs
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    if recursive_subfolders:
        logger.info(
            "When using recursive subfolder parsing same name images in different subfolders will overwrite each other."
        )
    if exclude_file_patterns is None:
        exclude_file_patterns = ["___save.png", "___fuse.png"]
    if extensions is None:
        extensions = ["jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp"]
    elif not isinstance(extensions, list):
        raise SABaseException(
            0,
            "extensions should be a list in upload_images_from_folder_to_project"
        )

    logger.info(
        "Uploading all images with extensions %s from %s to project %s. Excluded file patterns are: %s.",
        extensions, folder_path, project["name"], exclude_file_patterns
    )
    if from_s3_bucket is None:
        paths = []
        for extension in extensions:
            if not recursive_subfolders:
                paths += list(Path(folder_path).glob(f'*.{extension.lower()}'))
                if os.name != "nt":
                    paths += list(
                        Path(folder_path).glob(f'*.{extension.upper()}')
                    )
            else:
                paths += list(Path(folder_path).rglob(f'*.{extension.lower()}'))
                if os.name != "nt":
                    paths += list(
                        Path(folder_path).rglob(f'*.{extension.upper()}')
                    )
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
                    if key.endswith(f'.{extension.lower()}'
                                   ) or key.endswith(f'.{extension.upper()}'):
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


def create_empty_annotation(size, image_name):
    return {
        "metadata": {
            'height': size[1],
            'width': size[0],
            'name': image_name
        },
        "instances": [],
        "comments": [],
        "tags": []
    }


def upload_image_array_to_s3(
    bucket, size, orig_image, lores_image, huge_image, thumbnail_image, key,
    project_type
):
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
    postfix_json = '___objects.json' if project_type == "Vector" else '___pixel.json'
    bucket.put_object(
        Body=json.dumps(create_empty_annotation(size,
                                                Path(key).name)),
        Key=key + postfix_json
    )


def get_image_array_to_upload(
    byte_io_orig, image_quality_in_editor, project_type
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

    return (
        width, height
    ), byte_io_orig, byte_io_lores, byte_io_huge, byte_io_thumbs


def __upload_images_to_aws_thread(
    res, img_paths, project, annotation_status, prefix, thread_id, chunksize,
    couldnt_upload, uploaded, image_quality_in_editor, from_s3_bucket
):
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
        path = img_paths[i]
        key = prefix + f'{Path(path).name}'
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
                file, image_quality_in_editor, project["type"]
            )
            upload_image_array_to_s3(
                bucket, *images_array, key, project["type"]
            )
        except Exception as e:
            logger.warning("Unable to upload image %s. %s", path, e)
            couldnt_upload[thread_id].append(path)
            continue
        else:
            uploaded[thread_id].append(path)
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

    response = _api.send_request(
        req_type='POST', path='/image/ext-create', json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't ext-create image " + response.text
        )


def upload_images_to_project(
    project,
    img_paths,
    annotation_status="NotStarted",
    from_s3_bucket=None,
    image_quality_in_editor=None
):
    """Uploads all images given in list of path objects in img_paths to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    If an image with existing name already exists in the project it won't be uploaded,
    and its path will be appended to the third member of return value of this
    function.

    :param project: project name or metadata of the project to upload images to
    :type project: str or dict
    :param img_paths: list of Pathlike (str or Path) objects to upload
    :type img_paths: list
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded, could-not-upload, existing-images filepaths
    :rtype: tuple (3 members) of list of strs
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    if not isinstance(img_paths, list):
        raise SABaseException(
            0, "img_paths argument to upload_images_to_project should be a list"
        )
    annotation_status = common.annotation_status_str_to_int(annotation_status)
    if image_quality_in_editor is None:
        image_quality_in_editor = get_project_default_image_quality_in_editor(
            project
        )
    team_id, project_id = project["team_id"], project["id"]
    existing_images = search_images(project)
    duplicate_images = []
    for existing_image in existing_images:
        i = -1
        for j, img_path in enumerate(img_paths):
            if str(img_path).endswith(existing_image):
                i = j
                break
        if i != -1:
            duplicate_images.append(img_paths[i])
            del img_paths[i]
    if len(duplicate_images) != 0:
        logger.warning(
            "%s already existing images found that won't be uploaded.",
            len(duplicate_images)
        )
    len_img_paths = len(img_paths)
    logger.info(
        "Uploading %s images to project %s.", len_img_paths, project["name"]
    )
    if len_img_paths == 0:
        return ([], [], duplicate_images)
    params = {
        'team_id': team_id,
    }
    uploaded = []
    for _ in range(_NUM_THREADS):
        uploaded.append([])
    couldnt_upload = []
    for _ in range(_NUM_THREADS):
        couldnt_upload.append([])
    finish_event = threading.Event()
    chunksize = int(math.ceil(len(img_paths) / _NUM_THREADS))
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
    tqdm_thread = threading.Thread(
        target=__tqdm_thread_upload,
        args=(len_img_paths, uploaded, couldnt_upload, finish_event),
        daemon=True
    )
    tqdm_thread.start()

    threads = []
    for thread_id in range(_NUM_THREADS):
        t = threading.Thread(
            target=__upload_images_to_aws_thread,
            args=(
                res, img_paths, project, annotation_status, prefix, thread_id,
                chunksize, couldnt_upload, uploaded, image_quality_in_editor,
                from_s3_bucket
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
        for file in couldnt_upload_thread:
            list_of_not_uploaded.append(str(file))
    list_of_uploaded = []
    for upload_thread in uploaded:
        for file in upload_thread:
            list_of_uploaded.append(str(file))

    return (list_of_uploaded, list_of_not_uploaded, duplicate_images)


def upload_images_from_public_urls_to_project(
    project,
    img_urls,
    img_names=None,
    annotation_status='NotStarted',
    image_quality_in_editor=None
):
    """Uploads all images given in the list of URL strings in img_urls to the project.
    Sets status of all the uploaded images to annotation_status if it is not None.

    :param project: project name or metadata of the project to upload images to
    :type project: str or dict
    :param img_urls: list of str objects to upload
    :type img_urls: list
    :param img_names: list of str names for each urls in img_url list
    :type img_names: list
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded images' urls, uploaded images' filenames, duplicate images' filenames and not-uploaded images' urls
    :rtype: tuple of list of strs
    """

    if img_names is not None and len(img_names) != len(img_urls):
        raise SABaseException(0, "Not all image URLs have corresponding names.")

    images_not_uploaded = []
    images_to_upload = []
    duplicate_images_filenames = []
    path_to_url = {}
    with tempfile.TemporaryDirectory() as save_dir_name:
        save_dir = Path(save_dir_name)
        for i, img_url in enumerate(img_urls):
            try:
                response = requests.get(img_url)
                response.raise_for_status()
            except Exception as e:
                logger.warning(
                    "Couldn't download image %s, %s", img_url, str(e)
                )
                images_not_uploaded.append(img_url)
            else:
                if not img_names:
                    if response.headers.get('Content-Disposition') is not None:
                        img_path = save_dir / cgi.parse_header(
                            response.headers['Content-Disposition']
                        )[1]['filename']
                    else:
                        img_path = save_dir / basename(urlparse(img_url).path)
                else:
                    img_path = save_dir / img_names[i]

                if str(img_path) in path_to_url.keys():
                    duplicate_images_filenames.append(basename(img_path))
                    continue

                with open(img_path, 'wb') as f:
                    f.write(response.content)

                path_to_url[str(img_path)] = img_url
                images_to_upload.append(img_path)
        images_uploaded_paths, images_not_uploaded_paths, duplicate_images_paths = upload_images_to_project(
            project,
            images_to_upload,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor
        )
        images_not_uploaded.extend(
            [path_to_url[str(path)] for path in images_not_uploaded_paths]
        )
        images_uploaded = [
            path_to_url[str(path)] for path in images_uploaded_paths
        ]
        images_uploaded_filenames = [
            basename(path) for path in images_uploaded_paths
        ]
        duplicate_images_filenames.extend(
            [basename(path) for path in duplicate_images_paths]
        )
    return (
        images_uploaded, images_uploaded_filenames, duplicate_images_filenames,
        images_not_uploaded
    )


def upload_images_from_google_cloud_to_project(
    project,
    google_project,
    bucket_name,
    folder_path,
    annotation_status='NotStarted',
    image_quality_in_editor=None
):
    """Uploads all images present in folder_path at bucket_name in google_project to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: project name or metadata of the project to upload images to
    :type project: str or dict
    :param google_project: the project name on google cloud, where the bucket resides
    :type google_project: str
    :param bucket_name: the name of the bucket where the images are stored
    :type bucket_name: str
    :param folder_path: path of the folder on the bucket where the images are stored
    :type folder_path: str
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded images' urls, uploaded images' filenames, duplicate images' filenames and not-uploaded images' urls
    :rtype: tuple of list of strs
    """
    images_not_uploaded = []
    images_to_upload = []
    duplicate_images_filenames = []
    path_to_url = {}
    cloud_client = storage.Client(project=google_project)
    bucket = cloud_client.get_bucket(bucket_name)
    image_blobs = bucket.list_blobs(prefix=folder_path)
    with tempfile.TemporaryDirectory() as save_dir_name:
        save_dir = Path(save_dir_name)
        for image_blob in image_blobs:
            if image_blob.content_type.split('/')[0] != 'image':
                continue
            image_name = basename(image_blob.name)
            image_save_pth = save_dir / image_name
            if image_save_pth in path_to_url.keys():
                duplicate_images_filenames.append(basename(image_save_pth))
                continue
            try:
                image_blob.download_to_filename(image_save_pth)
            except Exception as e:
                logger.warning(
                    "Couldn't download image %s, %s", image_blob.name, str(e)
                )
                images_not_uploaded.append(image_blob.name)
            else:
                path_to_url[str(image_save_pth)] = image_blob.name
                images_to_upload.append(image_save_pth)
        images_uploaded_paths, images_not_uploaded_paths, duplicate_images_paths = upload_images_to_project(
            project,
            images_to_upload,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor
        )
        images_not_uploaded.extend(
            [path_to_url[str(path)] for path in images_not_uploaded_paths]
        )
        images_uploaded = [
            path_to_url[str(path)] for path in images_uploaded_paths
        ]
        images_uploaded_filenames = [
            basename(path) for path in images_uploaded_paths
        ]
        duplicate_images_filenames.extend(
            [basename(path) for path in duplicate_images_paths]
        )
    return (
        images_uploaded, images_uploaded_filenames, duplicate_images_filenames,
        images_not_uploaded
    )


def upload_images_from_azure_blob_to_project(
    project,
    container_name,
    folder_path,
    annotation_status='NotStarted',
    image_quality_in_editor=None
):
    """Uploads all images present in folder_path at container_name Azure blob storage to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: project name or metadata of the project to upload images to
    :type project: str or dict
    :param container_name: container name of the Azure blob storage
    :type container_name: str
    :param folder_path: path of the folder on the bucket where the images are stored
    :type folder_path: str
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded images' urls, uploaded images' filenames, duplicate images' filenames and not-uploaded images' urls
    :rtype: tuple of list of strs
    """
    images_not_uploaded = []
    images_to_upload = []
    duplicate_images_filenames = []
    path_to_url = {}
    connect_key = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    blob_service_client = BlobServiceClient.from_connection_string(connect_key)
    container_client = blob_service_client.get_container_client(container_name)
    image_blobs = container_client.list_blobs(name_starts_with=folder_path)
    with tempfile.TemporaryDirectory() as save_dir_name:
        save_dir = Path(save_dir_name)
        for image_blob in image_blobs:
            content_type = image_blob.content_settings.get('content_type')
            if content_type is None:
                logger.warning(
                    "Couldn't download image %s, content type could not be verified",
                    image_blob.name
                )
                continue
            if content_type.split('/')[0] != 'image':
                continue
            image_name = basename(image_blob.name)
            image_save_pth = save_dir / image_name
            if image_save_pth in path_to_url.keys():
                duplicate_images_filenames.append(basename(image_save_pth))
                continue
            try:
                image_blob_client = blob_service_client.get_blob_client(
                    container=container_name, blob=image_blob
                )
                image_stream = image_blob_client.download_blob()
            except Exception as e:
                logger.warning(
                    "Couldn't download image %s, %s", image_blob.name, str(e)
                )
                images_not_uploaded.append(image_blob.name)
            else:
                with open(image_save_pth, 'wb') as image_file:
                    image_file.write(image_stream.readall())
                path_to_url[str(image_save_pth)] = image_blob.name
                images_to_upload.append(image_save_pth)
        images_uploaded_paths, images_not_uploaded_paths, duplicate_images_paths = upload_images_to_project(
            project,
            images_to_upload,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor
        )
        images_not_uploaded.extend(
            [path_to_url[str(path)] for path in images_not_uploaded_paths]
        )
        images_uploaded = [
            path_to_url[str(path)] for path in images_uploaded_paths
        ]
        images_uploaded_filenames = [
            basename(path) for path in images_uploaded_paths
        ]
        duplicate_images_filenames.extend(
            [basename(path) for path in duplicate_images_paths]
        )
    return (
        images_uploaded, images_uploaded_filenames, duplicate_images_filenames,
        images_not_uploaded
    )


def __upload_annotations_thread(
    team_id, project_id, project_type, anns_filenames, folder_path,
    annotation_classes_dict, thread_id, chunksize, missing_images,
    couldnt_upload, uploaded, from_s3_bucket
):
    NUM_TO_SEND = 500
    len_anns = len(anns_filenames)
    start_index = thread_id * chunksize
    if start_index >= len_anns:
        return
    end_index = min(start_index + chunksize, len_anns)

    postfix_json = '___objects.json' if project_type == "Vector" else '___pixel.json'
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
        if len(res["images"]) < len(data["names"]):
            for name in data["names"]:
                if name not in res["images"]:
                    ann_path = Path(folder_path) / (name + postfix_json)
                    missing_images[thread_id].append(ann_path)
                    logger.warning(
                        "Couldn't find image %s for annotation upload", ann_path
                    )
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
                full_path = Path(folder_path) / json_filename
                annotation_json = json.load(open(full_path))
            else:
                file = io.BytesIO()
                full_path = folder_path + json_filename
                from_s3_object = from_s3.Object(from_s3_bucket, full_path)
                from_s3_object.download_fileobj(file)
                file.seek(0)
                annotation_json = json.load(file)

            if not check_annotation_json(annotation_json):
                couldnt_upload[thread_id].append(full_path)
                logger.warning(
                    "Annotation JSON %s missing width or height info", full_path
                )
                continue
            fill_class_and_attribute_ids(
                annotation_json, annotation_classes_dict
            )
            bucket.put_object(
                Key=image_path + postfix_json, Body=json.dumps(annotation_json)
            )
            if project_type != "Vector":
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
            uploaded[thread_id].append(full_path)


def upload_annotations_from_folder_to_project(
    project, folder_path, from_s3_bucket=None, recursive_subfolders=False
):
    """Finds and uploads all JSON files in the folder_path as annotations to the project.

    The JSON files should follow specific naming convention. For Vector
    projects they should be named "<image_filename>___objects.json" (e.g., if
    image is cats.jpg the annotation filename should be cats.jpg___objects.json), for Pixel projects
    JSON file should be named "<image_filename>___pixel.json" and also second mask
    image file should be present with the name "<image_name>___save.png". In both cases
    image with <image_name> should be already present on the platform.

    Existing annotations will be overwritten.

    :param project: project name or metadata of the project to upload annotations to
    :type project: str or dict
    :param folder_path: from which folder to upload the annotations
    :type folder_path: Pathlike (str or Path)
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool

    :return: paths to annotations uploaded, could-not-upload, missing-images
    :rtype: tuple of list of strs
    """
    if recursive_subfolders:
        logger.info(
            "When using recursive subfolder parsing same name annotations in different subfolders will overwrite each other."
        )

    logger.info(
        "The JSON files should follow specific naming convention. For Vector projects they should be named '<image_name>___objects.json', for Pixel projects JSON file should be names '<image_name>___pixel.json' and also second mask image file should be present with the name '<image_name>___save.png'. In both cases image with <image_name> should be already present on the platform."
    )

    logger.info("Existing annotations will be overwritten.")
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)

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
        "Uploading all annotations from %s to project %s.", folder_path,
        project["name"]
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
        "Uploading %s annotations to project %s.", len_annotations_paths,
        project["name"]
    )
    if len_annotations_paths == 0:
        return return_result
    uploaded = []
    for _ in range(_NUM_THREADS):
        uploaded.append([])
    couldnt_upload = []
    for _ in range(_NUM_THREADS):
        couldnt_upload.append([])
    missing_image = []
    for _ in range(_NUM_THREADS):
        missing_image.append([])
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=__tqdm_thread_upload_annotations,
        args=(
            len_annotations_paths, uploaded, couldnt_upload, missing_image,
            finish_event
        ),
        daemon=True
    )
    tqdm_thread.start()

    annotation_classes = search_annotation_classes(project)
    annotation_classes_dict = get_annotation_classes_name_to_id(
        annotation_classes
    )
    chunksize = int(math.ceil(len_annotations_paths / _NUM_THREADS))
    threads = []
    for thread_id in range(_NUM_THREADS):
        t = threading.Thread(
            target=__upload_annotations_thread,
            args=(
                team_id, project_id, project_type, annotations_filenames,
                folder_path, annotation_classes_dict, thread_id, chunksize,
                missing_image, couldnt_upload, uploaded, from_s3_bucket
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
        for file in couldnt_upload_thread:
            list_of_not_uploaded.append(str(file))
    list_of_uploaded = []
    for upload_thread in uploaded:
        for file in upload_thread:
            list_of_uploaded.append(str(file))
    list_of_missing_images = []
    for missing_thread in missing_image:
        for file in missing_thread:
            list_of_missing_images.append(str(file))
    # print(return_result)
    return (list_of_uploaded, list_of_not_uploaded, list_of_missing_images)


def __upload_preannotations_thread(
    aws_creds, project_type, preannotations_filenames, folder_path,
    annotation_classes_dict, thread_id, chunksize, couldnt_upload, uploaded,
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

    postfix_json = '___objects.json' if project_type == "Vector" else '___pixel.json'
    len_postfix_json = len(postfix_json)
    postfix_mask = '___save.png'
    if from_s3_bucket is not None:
        from_session = boto3.Session()
        from_s3 = from_session.resource('s3')

    for i in range(start_index, end_index):
        json_filename = preannotations_filenames[i]
        if from_s3_bucket is None:
            full_path = Path(folder_path) / json_filename
            annotation_json = json.load(open(full_path))
        else:
            file = io.BytesIO()
            full_path = folder_path + json_filename
            from_s3_object = from_s3.Object(from_s3_bucket, full_path)
            from_s3_object.download_fileobj(file)
            file.seek(0)
            annotation_json = json.load(file)

        if not check_annotation_json(annotation_json):
            couldnt_upload[thread_id].append(full_path)
            logger.warning(
                "Annotation JSON %s missing width or height info", full_path
            )
            continue
        fill_class_and_attribute_ids(annotation_json, annotation_classes_dict)
        bucket.put_object(
            Key=aws_creds["filePath"] + f"/{json_filename}",
            Body=json.dumps(annotation_json)
        )
        if project_type != "Vector":
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
        uploaded[thread_id].append(full_path)


def __tqdm_thread_upload(total_num, uploaded, couldnt_upload, finish_event):
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(5)
            if not finished:
                sum_all = 0
                for i in couldnt_upload:
                    sum_all += len(i)
                for i in uploaded:
                    sum_all += len(i)
                pbar.update(sum_all - pbar.n)
            else:
                pbar.update(total_num - pbar.n)
                break


def __tqdm_thread_upload_annotations(
    total_num, uploaded, couldnt_upload, missing_image, finish_event
):
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(5)
            if not finished:
                sum_all = 0
                for i in couldnt_upload:
                    sum_all += len(i)
                for i in uploaded:
                    sum_all += len(i)
                for i in missing_image:
                    sum_all += len(i)
                pbar.update(sum_all - pbar.n)
            else:
                pbar.update(total_num - pbar.n)
                break


def __tqdm_thread_upload_preannotations(
    total_num, uploaded, couldnt_upload, finish_event
):
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(5)
            if not finished:
                sum_all = 0
                for i in couldnt_upload:
                    sum_all += len(i)
                for i in uploaded:
                    sum_all += len(i)
                pbar.update(sum_all - pbar.n)
            else:
                pbar.update(total_num - pbar.n)
                break


def upload_preannotations_from_folder_to_project(
    project, folder_path, from_s3_bucket=None, recursive_subfolders=False
):
    """Finds and uploads all JSON files in the folder_path as pre-annotations to the project.

    The JSON files should follow specific naming convention. For Vector
    projects they should be named "<image_filename>___objects.json" (e.g., if
    image is cats.jpg the annotation filename should be cats.jpg___objects.json), for Pixel projects
    JSON file should be named "<image_filename>___pixel.json" and also second mask
    image file should be present with the name "<image_name>___save.png". In both cases
    image with <image_name> should be already present on the platform.

    Existing pre-annotations will be overwritten.

    :param project: project name or metadata of the project to upload pre-annotations to
    :type project: str or dict
    :param folder_path: from which folder to upload the pre-annotations
    :type folder_path: Pathlike (str or Path)
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool

    :return: paths to pre-annotations uploaded and could-not-upload
    :rtype: tuple of list of strs
    """
    if recursive_subfolders:
        logger.info(
            "When using recursive subfolder parsing same name pre-annotations in different subfolders will overwrite each other."
        )
    logger.info(
        "The JSON files should follow specific naming convention. For Vector projects they should be named '<image_name>___objects.json', for Pixel projects JSON file should be names '<image_name>___pixel.json' and also second mask image file should be present with the name '<image_name>___save.png'. In both cases image with <image_name> should be already present on the platform."
    )

    logger.info(
        "Identically named existing pre-annotations will be overwritten."
    )
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
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
        "Uploading all preannotations from %s to project %s.", folder_path,
        project["name"]
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
        "Uploading %s preannotations to project %s.", len_preannotations_paths,
        project["name"]
    )
    if len_preannotations_paths == 0:
        return return_result
    params = {
        'team_id': team_id,
        'creds_only': True,
        'type': common.project_type_str_to_int(project_type)
    }
    uploaded = []
    for _ in range(_NUM_THREADS):
        uploaded.append([])
    couldnt_upload = []
    for _ in range(_NUM_THREADS):
        couldnt_upload.append([])
    finish_event = threading.Event()
    chunksize = int(math.ceil(len_preannotations_paths / _NUM_THREADS))
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=__tqdm_thread_upload_preannotations,
        args=(len_preannotations_paths, couldnt_upload, uploaded, finish_event),
        daemon=True
    )
    tqdm_thread.start()
    annotation_classes = search_annotation_classes(project)
    annotation_classes_dict = get_annotation_classes_name_to_id(
        annotation_classes
    )
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
                aws_creds, project_type, preannotations_filenames, folder_path,
                annotation_classes_dict, thread_id, chunksize, couldnt_upload,
                uploaded, from_s3_bucket
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
        for file in couldnt_upload_thread:
            list_of_not_uploaded.append(str(file))
    list_of_uploaded = []
    for upload_thread in uploaded:
        for file in upload_thread:
            list_of_uploaded.append(str(file))
    return (list_of_uploaded, list_of_not_uploaded)


def share_project(project, user, user_role):
    """Share project with user.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param user: user email or metadata of the user to share project with
    :type user: str or dict
    :param user_role: user role to apply, one of Admin , Annotator , QA , Customer , Viewer
    :type user_role: str
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    if not isinstance(user, dict):
        user = get_team_contributor_metadata(user)
    user_role = common.user_role_str_to_int(user_role)
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
        "Shared project %s with user %s and role %s", project["name"],
        user["email"], common.user_role_int_to_str(user_role)
    )


def unshare_project(project, user):
    """Unshare (remove) user from project.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param user: user email or metadata of the user to unshare project
    :type user: str or dict
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    if not isinstance(user, dict):
        user = get_team_contributor_metadata(user)
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
    logger.info("Unshared project %s from user ID %s", project["name"], user_id)


def upload_images_from_s3_bucket_to_project(
    project,
    accessKeyId,
    secretAccessKey,
    bucket_name,
    folder_path,
    image_quality_in_editor=None
):
    """Uploads all images from AWS S3 bucket to the project.

    :param project: project name or metadata of the project to upload images to
    :type project: str or dict
    :param accessKeyId: AWS S3 access key ID
    :type accessKeyId: str
    :param secretAccessKey: AWS S3 secret access key
    :type secretAccessKey: str
    :param bucket_name: AWS S3 bucket
    :type bucket_name: str
    :param folder_path: from which folder to upload the images
    :type folder_path: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    if image_quality_in_editor is not None:
        old_quality = get_project_default_image_quality_in_editor(project)
        set_project_default_image_quality_in_editor(
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
        set_project_default_image_quality_in_editor(project, old_quality)


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


def get_project_workflow(project):
    """Gets project's workflow.

    Return value example: [{ "step" : <step_num>, "className" : <annotation_class>, "tool" : <tool_num>, ...},...]

    :param project: project name or metadata
    :type project: str or dict

    :return: project workflow
    :rtype: list of dicts
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    team_id, project_id = project["team_id"], project["id"]
    params = {
        "team_id": team_id,
    }
    response = _api.send_request(
        req_type='GET', path=f'/project/{project_id}/workflow', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't get project workflow " + response.text
        )
    res = response.json()
    annotation_classes = search_annotation_classes(project)
    for r in res:
        if "class_id" not in r:
            continue
        found_classid = False
        for a_class in annotation_classes:
            if a_class["id"] == r["class_id"]:
                found_classid = True
                r["className"] = a_class["name"]
                del r["class_id"]
                break
        if not found_classid:
            raise SABaseException(0, "Couldn't find class_id in workflow")
    return res


def set_project_workflow(project, new_workflow):
    """Sets project's workflow.

    new_workflow example: [{ "step" : <step_num>, "className" : <annotation_class>, "tool" : <tool_num>, ...},...]

    :param project: project name or metadata
    :type project: str or dict
    :param project: new workflow list of dicts
    :type project: list of dicts

    :return: updated part of project's workflow
    :rtype: list of dicts
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    if not isinstance(new_workflow, list):
        raise SABaseException(
            0, "Set project setting new_workflow should be a list"
        )
    team_id, project_id = project["team_id"], project["id"]

    params = {
        "team_id": team_id,
    }
    annotation_classes = search_annotation_classes(project)

    new_list = copy.deepcopy(new_workflow)
    for step in new_list:
        if "id" in step:
            del step["id"]
        if "className" in step:
            found = False
            for an_class in annotation_classes:
                if an_class["name"] == step["className"]:
                    step["class_id"] = an_class["id"]
                    del step["className"]
                    found = True
                    break
            if not found:
                raise SABaseException(
                    0, "Annotation class not found in set_project_workflow."
                )

    json_req = {"steps": new_list}
    response = _api.send_request(
        req_type='POST',
        path=f'/project/{project_id}/workflow',
        params=params,
        json_req=json_req
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't set project workflow " + response.text
        )
    res = response.json()
    return res


def get_project_settings(project):
    """Gets project's settings.

    Return value example: [{ "attribute" : "Brightness", "value" : 10, ...},...]

    :param project: project name or metadata
    :type project: str or dict

    :return: project settings
    :rtype: list of dicts
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
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
            "Couldn't get project settings " + response.text
        )
    res = response.json()
    for val in res:
        if val['attribute'] == 'ImageQuality':
            if val['value'] == 60:
                val['value'] = 'compressed'
            elif val['value'] == 100:
                val['value'] = 'original'
            else:
                raise SABaseException(0, "NA ImageQuality value")
    return res


def set_project_settings(project, new_settings):
    """Sets project's settings.

    New settings format example: [{ "attribute" : "Brightness", "value" : 10, ...},...]

    :param project: project name or metadata
    :type project: str or dict
    :param new_settings: new settings list of dicts
    :type new_settings: list of dicts

    :return: updated part of project's settings
    :rtype: list of dicts
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    if not isinstance(new_settings, list):
        raise SABaseException(
            0, "Set project setting new_settings should be a list"
        )
    team_id, project_id = project["team_id"], project["id"]

    params = {
        "team_id": team_id,
    }
    current_settings = get_project_settings(project)

    id_conv = {}
    for setting in current_settings:
        if "attribute" in setting:
            id_conv[setting["attribute"]] = setting["id"]

    new_list = []
    for new_setting in new_settings:
        if "attribute" in new_setting and new_setting["attribute"] in id_conv:
            new_list.append(
                {
                    "attribute": new_setting["attribute"],
                    "id": id_conv[new_setting["attribute"]],
                    "value": new_setting["value"]
                }
            )
    for val in new_list:
        if val['attribute'] == 'ImageQuality':
            if val['value'] == 'compressed':
                val['value'] = 60
            elif val['value'] == 'original':
                val['value'] = 100
            else:
                raise SABaseException(0, "NA ImageQuality value")
    json_req = {"settings": new_list}
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
    return response.json()


def set_project_default_image_quality_in_editor(
    project, image_quality_in_editor
):
    """Sets project's default image quality in editor setting.

    :param project: project name or metadata
    :type project: str or dict
    :param image_quality_in_editor: new setting value, should be "original" or "compressed"
    :type image_quality_in_editor: str
    """
    set_project_settings(
        project,
        [{
            "attribute": "ImageQuality",
            "value": image_quality_in_editor
        }]
    )


def get_project_default_image_quality_in_editor(project):
    """Gets project's default image quality in editor setting.

    :param project: project name or metadata
    :type project: str or dict

    :return: "original" or "compressed" setting value
    :rtype: str
    """
    for setting in get_project_settings(project):
        if "attribute" in setting and setting["attribute"] == "ImageQuality":
            return setting["value"]
    else:
        raise SABaseException(
            0,
            "Image quality in editor should be 'compressed', 'original' or None for project settings value"
        )
