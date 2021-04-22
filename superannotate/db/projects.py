import cgi
import copy
import io
import json
import logging
import math
import os
import tempfile
import threading
import time
import uuid
import pandas as pd
from os.path import basename
from pathlib import Path
from urllib.parse import urlparse

import boto3
import cv2
import ffmpeg
import requests
from azure.storage.blob import BlobServiceClient
from google.cloud import storage

from .. import common
from ..api import API
from ..exceptions import (
    SABaseException, SAExistingProjectNameException,
    SANonExistingProjectNameException
)
from .annotation_classes import (
    check_annotation_json, create_annotation_classes_from_classes_json,
    fill_class_and_attribute_ids, get_annotation_classes_name_to_id,
    search_annotation_classes
)
from .images import get_image_metadata, search_images, search_images_all_folders, get_project_root_folder_id
from .project_api import (
    get_project_and_folder_metadata, get_project_metadata_bare,
    get_project_metadata_with_users
)
from .users import get_team_contributor_metadata
from .utils import _get_upload_auth_token, _get_boto_session_by_credentials, _upload_images, _attach_urls
from tqdm import tqdm

_NUM_THREADS = 10
_TIME_TO_UPDATE_IN_TQDM = 1
logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()


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
    if len(
        set(project_name).intersection(
            common.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
        )
    ) > 0:
        logger.warning(
            "New project name has special characters. Special characters will be replaced by underscores."
        )
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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


def get_project_image_count(project, with_all_subfolders=False):
    """Returns number of images in the project.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param with_all_subfolders: enables recursive folder counting
    :type with_all_subfolders: bool

    :return: number of images in the project
    :rtype: int
    """
    if not with_all_subfolders:
        return len(search_images(project))
    else:
        return len(search_images_all_folders(project))


def _get_video_frames_count(video_path):
    """
    Get video frames count
    """
    video = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    total_num_of_frames = 0
    flag = True
    while flag:
        flag, _ = video.read()
        if flag:
            total_num_of_frames += 1
        else:
            break
    return total_num_of_frames


def _get_video_fps_ration(target_fps, video, ratio):
    """
    Get video fps / target fps ratio
    """
    video_fps = float(video.get(cv2.CAP_PROP_FPS))
    if target_fps >= video_fps:
        logger.warning(
            "Video frame rate %s smaller than target frame rate %s. Cannot change frame rate.",
            video_fps, target_fps
        )
    else:
        logger.info(
            "Changing video frame rate from %s to target frame rate %s.",
            video_fps, target_fps
        )
        ratio = video_fps / target_fps
    return ratio


def _get_available_image_counts(project, folder):
    if folder:
        folder_id = folder["id"]
    else:
        folder_id = get_project_root_folder_id(project)
    params = {'team_id': project['team_id'], 'folder_id': folder_id}
    res = _get_upload_auth_token(params=params, project_id=project['id'])
    return res['availableImageCount']


def _get_video_rotate_code(video_path):
    rotate_code = None
    try:
        cv2_rotations = {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE,
        }

        meta_dict = ffmpeg.probe(str(video_path))
        rot = int(meta_dict['streams'][0]['tags']['rotate'])
        rotate_code = cv2_rotations[rot]
        if rot != 0:
            logger.info(
                "Frame rotation of %s found. Output images will be rotated accordingly.",
                rot
            )
    except Exception as e:
        warning_str = ""
        if "ffprobe" in str(e):
            warning_str = "This could be because ffmpeg package is not installed. To install it, run: sudo apt install ffmpeg"
        logger.warning(
            "Couldn't read video metadata to determine rotation. %s",
            warning_str
        )
    return rotate_code


def _extract_frames_from_video(
    start_time, end_time, video_path, tempdir, limit, target_fps
):
    video = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    if not video.isOpened():
        raise SABaseException(0, "Couldn't open video file " + str(video_path))
    total_num_of_frames = _get_video_frames_count(video_path)
    logger.info("Video frame count is %s.", total_num_of_frames)
    ratio = 1.0
    if target_fps:
        ratio = _get_video_fps_ration(target_fps, video, ratio)
    rotate_code = _get_video_rotate_code(video_path)
    video_name = Path(video_path).stem
    frame_no = 0
    frame_no_with_change = 1.0
    extracted_frame_no = 1
    logger.info("Extracting frames from video to %s.", tempdir.name)
    zero_fill_count = len(str(total_num_of_frames))
    extracted_frames_paths = []
    while len(extracted_frames_paths) < limit:
        success, frame = video.read()
        if not success:
            break
        frame_no += 1
        if round(frame_no_with_change) != frame_no:
            continue
        frame_no_with_change += ratio
        frame_time = video.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if end_time and frame_time > end_time:
            break
        if frame_time < start_time:
            continue
        if rotate_code:
            frame = cv2.rotate(frame, rotate_code)
        path = str(
            Path(tempdir.name) / (
                video_name + "_" +
                str(extracted_frame_no).zfill(zero_fill_count) + ".jpg"
            )
        )
        cv2.imwrite(path, frame)
        extracted_frames_paths.append(path)
        extracted_frame_no += 1
    return extracted_frames_paths


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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

    project, folder = get_project_and_folder_metadata(project)
    limit = _get_available_image_counts(project, folder)

    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
    logger.info("Uploading from video %s.", str(video_path))
    tempdir = tempfile.TemporaryDirectory()
    extracted_frames = _extract_frames_from_video(
        start_time, end_time, video_path, tempdir, limit, target_fps
    )
    logger.info(
        "Extracted %s frames from video. Now uploading to platform.",
        len(extracted_frames)
    )
    filenames = upload_images_from_folder_to_project(
        (project, folder),
        tempdir.name,
        extensions=["jpg"],
        annotation_status=annotation_status,
        image_quality_in_editor=image_quality_in_editor
    )

    filenames_base = [Path(f).name for f in filenames[0]]
    return filenames_base


def upload_videos_from_folder_to_project(
    project,
    folder_path,
    extensions=common.DEFAULT_VIDEO_EXTENSIONS,
    exclude_file_patterns=(),
    recursive_subfolders=False,
    target_fps=None,
    start_time=0.0,
    end_time=None,
    annotation_status="NotStarted",
    image_quality_in_editor=None
):
    """Uploads image frames from all videos with given extensions from folder_path to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param folder_path: from which folder to upload the videos
    :type folder_path: Pathlike (str or Path)
    :param extensions: tuple or list of filename extensions to include from folder 
    :type extensions: tuple or list of strs
    :param exclude_file_patterns: filename patterns to exclude from uploading
    :type exclude_file_patterns: listlike of strs
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
    project, folder = get_project_and_folder_metadata(project)
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
    if recursive_subfolders:
        logger.warning(
            "When using recursive subfolder parsing same name videos in different subfolders will overwrite each other."
        )
    if not isinstance(extensions, (list, tuple)):
        raise SABaseException(
            0,
            "extensions should be a list or a tuple in upload_images_from_folder_to_project"
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
            (project, folder),
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
    extensions=common.DEFAULT_IMAGE_EXTENSIONS,
    annotation_status="NotStarted",
    from_s3_bucket=None,
    exclude_file_patterns=common.DEFAULT_FILE_EXCLUDE_PATTERNS,
    recursive_subfolders=False,
    image_quality_in_editor=None
):
    """Uploads all images with given extensions from folder_path to the project.
    Sets status of all the uploaded images to set_status if it is not None.

    If an image with existing name already exists in the project it won't be uploaded,
    and its path will be appended to the third member of return value of this
    function.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param folder_path: from which folder to upload the images
    :type folder_path: Pathlike (str or Path)
    :param extensions: tuple or list of filename extensions to include from folder
    :type extensions: tuple or list of strs
    :param annotation_status: value to set the annotation statuses of the uploaded images NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param exclude_file_patterns: filename patterns to exclude from uploading,
                                 default value is to exclude SuperAnnotate export related ["___save.png", "___fuse.png"]
    :type exclude_file_patterns: list or tuple of strs
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str

    :return: uploaded, could-not-upload, existing-images filepaths
    :rtype: tuple (3 members) of list of strs
    """
    project, project_folder = get_project_and_folder_metadata(project)
    project_folder_name = project["name"] + (
        f'/{project_folder["name"]}' if project_folder else ""
    )
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
    if recursive_subfolders:
        logger.info(
            "When using recursive subfolder parsing same name images in different subfolders will overwrite each other."
        )
    if not isinstance(extensions, (list, tuple)):
        raise SABaseException(
            0,
            "extensions should be a list or a tuple in upload_images_from_folder_to_project"
        )

    logger.info(
        "Uploading all images with extensions %s from %s to project %s. Excluded file patterns are: %s.",
        extensions, folder_path, project_folder_name, exclude_file_patterns
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
        (project, project_folder), filtered_paths, annotation_status,
        from_s3_bucket, image_quality_in_editor
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    project, folder = get_project_and_folder_metadata(project)
    folder_name = project["name"] + (f'/{folder["name"]}' if folder else "")
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
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

    if folder:
        folder_id = folder["id"]
    else:
        folder_id = get_project_root_folder_id(project)

    list_of_uploaded, list_of_not_uploaded, duplicate_images = _upload_images(
        img_paths=img_paths,
        team_id=team_id,
        folder_id=folder_id,
        project_id=project_id,
        annotation_status=annotation_status,
        from_s3_bucket=from_s3_bucket,
        image_quality_in_editor=image_quality_in_editor,
        project=project,
        folder_name=folder_name
    )

    return (list_of_uploaded, list_of_not_uploaded, duplicate_images)


def _tqdm_download(
    total_num, images_to_upload, images_not_uploaded,
    duplicate_images_filenames, finish_event
):
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(1)
            if not finished:
                sum_all = 0
                sum_all += len(images_not_uploaded)
                sum_all += len(images_to_upload)
                sum_all += len(duplicate_images_filenames)
                pbar.update(sum_all - pbar.n)
            else:
                pbar.update(total_num - pbar.n)
                break


def attach_image_urls_to_project(
    project, attachments, annotation_status="NotStarted"
):
    """Link images on external storage to SuperAnnotate.
    
    :param project: project name or project folder path
    :type project: str or dict
    :param attachments: path to csv file on attachments metadata
    :type attachments: Pathlike (str or Path)
    :param annotation_status: value to set the annotation statuses of the linked images: NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str

    :return: list of linked image names, list of failed image names, list of duplicate image names
    :rtype: tuple
    """
    project, folder = get_project_and_folder_metadata(project)
    folder_name = project["name"] + (f'/{folder["name"]}' if folder else "")
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "Basic":
        raise SABaseException(
            0,
            "You cannot attach URLs in this type of project. Please attach it in an external storage project"
        )
    annotation_status = common.annotation_status_str_to_int(annotation_status)
    team_id, project_id = project["team_id"], project["id"]
    image_data = pd.read_csv(attachments, dtype=str)
    image_data = image_data[~image_data["url"].isnull()]
    for ind, _ in image_data[image_data["name"].isnull()].iterrows():
        name_try = str(uuid.uuid4())
        image_data.at[ind, "name"] = name_try
    image_data = pd.DataFrame(image_data, columns=["name", "url"])
    img_names_urls = image_data.values.tolist()

    if folder:
        folder_id = folder["id"]
    else:
        folder_id = get_project_root_folder_id(project)

    list_of_uploaded, list_of_not_uploaded, duplicate_images = _attach_urls(
        img_names_urls=img_names_urls,
        team_id=team_id,
        folder_id=folder_id,
        project_id=project_id,
        annotation_status=annotation_status,
        project=project,
        folder_name=folder_name
    )

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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    project, project_folder = get_project_and_folder_metadata(project)
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=_tqdm_download,
        args=(
            len(img_urls), images_to_upload, images_not_uploaded,
            duplicate_images_filenames, finish_event
        ),
        daemon=True
    )
    logger.info('Downloading %s images', len(img_urls))
    tqdm_thread.start()
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

        finish_event.set()
        tqdm_thread.join()
        images_uploaded_paths, images_not_uploaded_paths, duplicate_images_paths = upload_images_to_project(
            (project, project_folder),
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    project, project_folder = get_project_and_folder_metadata(project)
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
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
            (project, project_folder),
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    project, project_folder = get_project_and_folder_metadata(project)
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
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
            (project, project_folder),
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
    annotation_classes_dict, pre, thread_id, chunksize, missing_images,
    couldnt_upload, uploaded, from_s3_bucket, project_folder_id
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
        names = []
        for j in range(i, i + NUM_TO_SEND):
            if j >= end_index:
                break
            image_name = anns_filenames[j][:-len_postfix_json]
            names.append(image_name)
        try:
            metadatas = get_image_metadata(
                ({
                    "id": project_id
                }, {
                    "id": project_folder_id
                }), names, False
            )
        except SABaseException:
            metadatas = []
        names_in_metadatas = [metadata["name"] for metadata in metadatas]
        id_to_name = {
            metadata["id"]: metadata["name"]
            for metadata in metadatas
        }
        if len(metadatas) < len(names):
            for name in names:
                if name not in names_in_metadatas:
                    ann_path = Path(folder_path) / (name + postfix_json)
                    missing_images[thread_id].append(ann_path)
                    logger.warning(
                        "Couldn't find image %s for annotation upload", ann_path
                    )
        data = {
            "project_id": project_id,
            "team_id": team_id,
            "ids": [metadata["id"] for metadata in metadatas],
            "folder_id": project_folder_id
        }
        endpoint = '/images/getAnnotationsPathsAndTokens' if pre == "" else '/images/getPreAnnotationsPathsAndTokens'
        response = _api.send_request(
            req_type='POST', path=endpoint, json_req=data
        )
        if not response.ok:
            logger.warning(
                "Couldn't get token upload annotations %s", response.text
            )
            continue
        res = response.json()
        aws_creds = res["creds"]
        s3_session = _get_boto_session_by_credentials(aws_creds)
        s3_resource = s3_session.resource('s3')
        bucket = s3_resource.Bucket(aws_creds["bucket"])
        for image_id, image_info in res['images'].items():
            image_name = id_to_name[int(image_id)]
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
                    "Annotation JSON %s missing width or height info. Skipping upload",
                    full_path
                )
                continue
            fill_class_and_attribute_ids(
                annotation_json, annotation_classes_dict
            )
            bucket.put_object(
                Key=image_info["annotation_json_path"],
                Body=json.dumps(annotation_json)
            )
            if project_type == "Pixel":
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
                bucket.put_object(
                    Key=image_info["annotation_bluemap_path"], Body=file
                )
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool

    :return: paths to annotations uploaded, could-not-upload, missing-images
    :rtype: tuple of list of strs
    """
    return _upload_pre_or_annotations_from_folder_to_project(
        project, folder_path, "", from_s3_bucket, recursive_subfolders
    )


def _upload_pre_or_annotations_from_folder_to_project(
    project, folder_path, pre, from_s3_bucket=None, recursive_subfolders=False
):
    if recursive_subfolders:
        logger.info(
            "When using recursive subfolder parsing same name %sannotations in different subfolders will overwrite each other.",
            pre
        )

    logger.info(
        "The JSON files should follow specific naming convention. For Vector projects they should be named '<image_name>___objects.json', for Pixel projects JSON file should be names '<image_name>___pixel.json' and also second mask image file should be present with the name '<image_name>___save.png'. In both cases image with <image_name> should be already present on the platform."
    )

    logger.info("Existing %sannotations will be overwritten.", pre)
    project, project_folder = get_project_and_folder_metadata(project)

    if project_folder is not None:
        project_folder_id = project_folder["id"]
    else:
        project_folder_id = None

    return _upload_annotations_from_folder_to_project(
        project, folder_path, pre, from_s3_bucket, recursive_subfolders,
        project_folder_id
    )


def _upload_annotations_from_folder_to_project(
    project,
    folder_path,
    pre,
    from_s3_bucket=None,
    recursive_subfolders=False,
    project_folder_id=None
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
                        project, path, pre, from_s3_bucket,
                        recursive_subfolders, project_folder_id
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
                        project, o.get('Prefix'), pre, from_s3_bucket,
                        recursive_subfolders, project_folder_id
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
                folder_path, annotation_classes_dict, pre, thread_id, chunksize,
                missing_image, couldnt_upload, uploaded, from_s3_bucket,
                project_folder_id
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


def __tqdm_thread_upload_annotations(
    total_num, uploaded, couldnt_upload, missing_image, finish_event
):
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(_TIME_TO_UPDATE_IN_TQDM)
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param folder_path: from which folder to upload the pre-annotations
    :type folder_path: Pathlike (str or Path)
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param recursive_subfolders: enable recursive subfolder parsing
    :type recursive_subfolders: bool

    :return: paths to pre-annotations uploaded and could-not-upload
    :rtype: tuple of list of strs
    """
    return _upload_pre_or_annotations_from_folder_to_project(
        project, folder_path, "pre", from_s3_bucket, recursive_subfolders
    )


def share_project(project, user, user_role):
    """Share project with user.

    :param project: project name
    :type project: str
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

    :param project: project name
    :type project: str
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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
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
    project, project_folder = get_project_and_folder_metadata(project)
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
    if project_folder is not None:
        data["folder_id"] = project_folder["id"]

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
        res = _get_upload_from_s3_bucket_to_project_status(
            project, project_folder
        )
        if res["progress"] == '2':
            break
        if res["progress"] != "1":
            raise SABaseException(
                response.status_code,
                "Couldn't upload to project from S3 " + str(res)
            )
    if image_quality_in_editor is not None:
        set_project_default_image_quality_in_editor(project, old_quality)


def _get_upload_from_s3_bucket_to_project_status(project, project_folder):
    team_id, project_id = project["team_id"], project["id"]
    params = {
        "team_id": team_id,
    }
    if project_folder is not None:
        params["folder_id"] = project_folder["id"]
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

    new_workflow example: [{ "step" : <step_num>, "className" : <annotation_class>, "tool" : <tool_num>,
                          "attribute":[{"attribute" : {"name" : <attribute_value>, "attribute_group" : {"name": <attribute_group>}}},
                          ...]
                          },...]

    :param project: project name or metadata
    :type project: str or dict
    :param project: new workflow list of dicts
    :type project: list of dicts
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
        if "className" not in step:
            continue
        for an_class in annotation_classes:
            if an_class["name"] == step["className"]:
                step["class_id"] = an_class["id"]
                break
        else:
            raise SABaseException(
                0, "Annotation class not found in set_project_workflow."
            )
        json_req = {"steps": [step]}
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
        if "attribute" not in step:
            continue
        current_steps = get_project_workflow(project)
        for step_in_response in current_steps:
            if step_in_response["step"] == step["step"]:
                workflow_id = step_in_response["id"]
                break
        else:
            raise SABaseException(0, "Couldn't find step in workflow")
        request_data = []
        for attribute in step["attribute"]:
            for att_class in an_class["attribute_groups"]:
                if att_class["name"] == attribute["attribute"]["attribute_group"
                                                              ]["name"]:
                    break
            else:
                raise SABaseException(
                    0, "Attribute group not found in set_project_workflow."
                )
            for att_value in att_class["attributes"]:
                if att_value["name"] == attribute["attribute"]["name"]:
                    attribute_id = att_value["id"]
                    break
            else:
                raise SABaseException(
                    0, "Attribute value not found in set_project_workflow."
                )

            request_data.append(
                {
                    "workflow_id": workflow_id,
                    "attribute_id": attribute_id
                }
            )

        response = _api.send_request(
            req_type='POST',
            path=f'/project/{project_id}/workflow_attribute',
            params=params,
            json_req={"data": request_data}
        )
        if not response.ok:
            raise SABaseException(
                response.status_code,
                "Couldn't set project workflow " + response.text
            )


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
    raise SABaseException(
        0,
        "Image quality in editor should be 'compressed', 'original' or None for project settings value"
    )


def get_project_metadata(
    project,
    include_annotation_classes=False,
    include_settings=False,
    include_workflow=False,
    include_contributors=False,
    include_complete_image_count=False
):
    """Returns project metadata

    :param project: project name
    :type project: str
    :param include_annotation_classes: enables project annotation classes output under
                                       the key "annotation_classes"
    :type include_annotation_classes: bool
    :param include_settings: enables project settings output under
                             the key "settings"
    :type include_settings: bool
    :param include_workflow: enables project workflow output under
                             the key "workflow"
    :type include_workflow: bool
    :param include_contributors: enables project contributors output under
                             the key "contributors"
    :type include_contributors: bool

    :return: metadata of project
    :rtype: dict
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(
            project, include_complete_image_count
        )
    result = copy.deepcopy(project)
    if include_annotation_classes:
        result["annotation_classes"] = search_annotation_classes(project)
    if include_contributors:
        result["contributors"] = get_project_metadata_with_users(project
                                                                )["users"]
    if include_settings:
        result["settings"] = get_project_settings(project)
    if include_workflow:
        result["workflow"] = get_project_workflow(project)
    return result


def clone_project(
    project_name,
    from_project,
    project_description=None,
    copy_annotation_classes=True,
    copy_settings=True,
    copy_workflow=True,
    copy_contributors=False
):
    """Create a new project in the team using annotation classes and settings from from_project.

    :param project_name: new project's name
    :type project_name: str
    :param from_project: the name of the project being used for duplication
    :type from_project: str
    :param project_description: the new project's description. If None, from_project's
                                description will be used
    :type project_description: str
    :param copy_annotation_classes: enables copying annotation classes
    :type copy_annotation_classes: bool
    :param copy_settings: enables copying project settings
    :type copy_settings: bool
    :param copy_workflow: enables copying project workflow
    :type copy_workflow: bool
    :param copy_contributors: enables copying project contributors
    :type copy_contributors: bool

    :return: dict object metadata of the new project
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
    metadata = get_project_metadata(
        from_project, copy_annotation_classes, copy_settings, copy_workflow,
        copy_contributors
    )
    metadata["name"] = project_name
    if project_description is not None:
        metadata["description"] = project_description

    return create_project_from_metadata(metadata)