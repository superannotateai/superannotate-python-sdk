import io
import logging
import re
import time
from pathlib import Path

import boto3

from .. import common
from ..api import API
from ..exceptions import SABaseException, SAImageSizeTooLarge
from .images import (
    delete_image, get_image_annotations, get_image_bytes, get_image_metadata,
    get_project_root_folder_id, search_images, set_image_annotation_status,
    upload_image_annotations
)
from .project_api import get_project_and_folder_metadata
from .projects import (
    get_project_default_image_quality_in_editor, _get_available_image_counts
)
from .utils import _get_upload_auth_token, _get_boto_session_by_credentials, upload_image_array_to_s3, get_image_array_to_upload, __create_image

logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


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

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param img: image to upload
    :type img: io.BytesIO() or Pathlike (str or Path)
    :param image_name: image name to set on platform. If None and img is filepath,
                       image name will be set to filename of the path
    :type image_name: str
    :param annotation_status: value to set the annotation statuses of the uploaded image NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_status: str
    :param from_s3_bucket: AWS S3 bucket to use. If None then folder_path is in local filesystem
    :type from_s3_bucket: str
    :param image_quality_in_editor: image quality be seen in SuperAnnotate web annotation editor.
           Can be either "compressed" or "original".  If None then the default value in project settings will be used.
    :type image_quality_in_editor: str
    """
    initial_project_inp = project
    project, folder = get_project_and_folder_metadata(project)
    upload_state = common.upload_state_int_to_str(project.get("upload_state"))
    if upload_state == "External":
        raise SABaseException(
            0,
            "The function does not support projects containing images attached with URLs"
        )
    annotation_status = common.annotation_status_str_to_int(annotation_status)
    if image_quality_in_editor is None:
        image_quality_in_editor = get_project_default_image_quality_in_editor(
            project
        )

    img_name = None
    if not isinstance(img, io.BytesIO):
        img_name = Path(img).name
        if from_s3_bucket is not None:
            from_session = boto3.Session()
            from_s3 = from_session.resource('s3')
            from_s3_object = from_s3.Object(from_s3_bucket, img)
            file_size = from_s3_object.content_length
            if file_size > common.MAX_IMAGE_SIZE:
                raise SAImageSizeTooLarge(file_size, img)
            img = io.BytesIO()
            from_s3_object.download_fileobj(img)
        else:
            file_size = Path(img).stat().st_size
            if file_size > common.MAX_IMAGE_SIZE:
                raise SAImageSizeTooLarge(file_size, img)
            with open(img, "rb") as f:
                img = io.BytesIO(f.read())
    elif img.getbuffer().nbytes > common.MAX_IMAGE_SIZE:
        raise SAImageSizeTooLarge(img.getbuffer().nbytes)

    if image_name is not None:
        img_name = image_name

    if img_name is None:
        raise SABaseException(
            0, "Image name img_name should be set if img is not Pathlike"
        )

    if folder:
        folder_id = folder["id"]
    else:
        folder_id = get_project_root_folder_id(project)

    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': team_id, 'folder_id': folder_id}
    res = _get_upload_auth_token(params=params, project_id=project_id)
    prefix = res['filePath']
    s3_session = _get_boto_session_by_credentials(res)
    s3_resource = s3_session.resource('s3')
    bucket = s3_resource.Bucket(res["bucket"])
    try:
        images_info_and_array = get_image_array_to_upload(
            img_name, img, image_quality_in_editor, project["type"]
        )
        key = upload_image_array_to_s3(bucket, *images_info_and_array, prefix)
    except Exception as e:
        raise SABaseException(0, "Couldn't upload to data server.") from e

    __create_image(
        [img_name], [key],
        project,
        annotation_status,
        prefix, [images_info_and_array[2]],
        folder_id,
        upload_state="Basic"
    )

    while True:
        try:
            get_image_metadata(initial_project_inp, img_name)
        except SABaseException:
            time.sleep(0.2)
        else:
            break


def _copy_images(
    source_project, destination_project, image_names, include_annotations,
    copy_annotation_status, copy_pin
):
    NUM_TO_SEND = 500
    source_project, source_project_folder = source_project
    destination_project, destination_project_folder = destination_project
    if source_project["id"] != destination_project["id"]:
        raise SABaseException(
            0,
            "Source and destination projects should be the same for copy_images"
        )
    params = {
        "team_id": source_project["team_id"],
        "project_id": source_project["id"]
    }
    if source_project_folder is not None:
        source_folder_name = source_project_folder["name"]
    else:
        source_folder_name = 'root'
    json_req = {"source_folder_name": source_folder_name}
    if destination_project_folder is not None:
        destination_folder_id = destination_project_folder["id"]
    else:
        destination_folder_id = get_project_root_folder_id(destination_project)
    json_req["destination_folder_id"] = destination_folder_id
    res = {}
    res['skipped'] = []
    res['completed'] = []
    for start_index in range(0, len(image_names), NUM_TO_SEND):
        json_req["image_names"] = image_names[start_index:start_index +
                                              NUM_TO_SEND]
        response = _api.send_request(
            req_type='POST',
            path='/image/copy',
            params=params,
            json_req=json_req
        )

        if not response.ok:
            raise SABaseException(
                response.status_code, "Couldn't copy images " + response.text
            )
        res['skipped'] += response.json()['skipped']
        res['completed'] += response.json()['completed']

    for image_name in image_names:
        _copy_annotations_and_metadata(
            source_project, source_project_folder, image_name,
            destination_project, destination_project_folder, image_name,
            include_annotations, copy_annotation_status, copy_pin
        )
    return res


def copy_images(
    source_project,
    image_names,
    destination_project,
    include_annotations=True,
    copy_annotation_status=True,
    copy_pin=True
):
    """Copy images in bulk between folders in a project 

    :param source_project: project name or folder path (e.g., "project1/folder1")
    :type source_project: str
    :param image_names: image names. If None, all images from source project will be copied
    :type image: list of str
    :param destination_project: project name or folder path (e.g., "project1/folder2")
    :type destination_project: str
    :param include_annotations: enables annotations copy
    :type include_annotations: bool
    :param copy_annotation_status: enables annotations status copy
    :type copy_annotation_status: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    :return: list of skipped image names
    :rtype: list of strs
    """
    source_project, source_project_folder = get_project_and_folder_metadata(
        source_project
    )
    destination_project, destination_project_folder = get_project_and_folder_metadata(
        destination_project
    )
    if image_names is None:
        image_names = search_images((source_project, source_project_folder))

    limit = _get_available_image_counts(
        destination_project, destination_project_folder
    )
    imgs_to_upload = image_names[:limit]
    res = _copy_images(
        (source_project, source_project_folder),
        (destination_project, destination_project_folder), imgs_to_upload,
        include_annotations, copy_annotation_status, copy_pin
    )
    uploaded_imgs = res['completed']
    skipped_imgs = [i for i in imgs_to_upload if i not in uploaded_imgs]

    skipped_images_count = len(skipped_imgs) + len(image_names[limit:])

    logger.info(
        "Copied images %s from %s to %s. Number of skipped images %s",
        uploaded_imgs, source_project["name"] +
        "" if source_project_folder is None else source_project["name"] + "/" +
        source_project_folder["name"], destination_project["name"] + ""
        if destination_project_folder is None else destination_project["name"] +
        "/" + destination_project_folder["name"], skipped_images_count
    )
    return skipped_imgs


def delete_images(project, image_names):
    """Delete images in project.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_names: to be deleted images' names. If None, all the images will be deleted
    :type image_names: list of strs
    """
    NUM_TO_SEND = 1000
    project, project_folder = get_project_and_folder_metadata(project)
    params = {"team_id": project["team_id"], "project_id": project["id"]}
    if image_names is None:
        images = search_images((project, project_folder), return_metadata=True)
    else:
        if not isinstance(image_names, list):
            raise SABaseException(
                0, "image_names should be a list of strs or None"
            )
        images = get_image_metadata(
            (project, project_folder),
            image_names,
            return_dict_on_single_output=False
        )
    for start_index in range(0, len(images), NUM_TO_SEND):
        data = {
            "image_ids":
                [
                    image["id"]
                    for image in images[start_index:start_index + NUM_TO_SEND]
                ]
        }
        response = _api.send_request(
            req_type='PUT',
            path='/image/delete/images',
            params=params,
            json_req=data
        )
        if not response.ok:
            raise SABaseException(
                response.status_code, "Couldn't delete images " + response.text
            )
    logger.info(
        "Images deleted in project %s%s", project["name"],
        "" if project_folder is None else "/" + project_folder["name"]
    )


def move_images(
    source_project,
    image_names,
    destination_project,
    include_annotations=True,
    copy_annotation_status=True,
    copy_pin=True,
):
    """Move images in bulk between folders in a project 

    :param source_project: project name or folder path (e.g., "project1/folder1")
    :type source_project: str
    :param image_names: image names. If None, all images from source project will be moved
    :type image: list of str
    :param destination_project: project name or folder path (e.g., "project1/folder2")
    :type destination_project: str
    :param include_annotations: enables annotations copy
    :type include_annotations: bool
    :param copy_annotation_status: enables annotations status copy
    :type copy_annotation_status: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    """
    source_project, source_project_folder = get_project_and_folder_metadata(
        source_project
    )
    destination_project, destination_project_folder = get_project_and_folder_metadata(
        destination_project
    )
    if image_names is None:
        image_names = search_images((source_project, source_project_folder))
    copy_images(
        (source_project, source_project_folder), image_names,
        (destination_project, destination_project_folder), include_annotations,
        copy_annotation_status, copy_pin
    )
    delete_images((source_project, source_project_folder), image_names)
    logger.info(
        "Moved images %s from project %s to project %s", image_names,
        source_project["name"] + "" if source_project_folder is None else "/" +
        source_project_folder["name"], destination_project["name"] +
        "" if destination_project_folder is None else "/" +
        destination_project_folder["name"]
    )


def copy_image(
    source_project,
    image_name,
    destination_project,
    include_annotations=False,
    copy_annotation_status=False,
    copy_pin=False
):
    """Copy image to a project. The image's project is the same as destination
    project then the name will be changed to <image_name>_(<num>).<image_ext>,
    where <num> is the next available number deducted from project image list.

    :param source_project: project name plus optional subfolder in the project (e.g., "project1/folder1") or
                           metadata of the project of source project
    :type source_project: str or dict
    :param image_name: image name
    :type image: str
    :param destination_project: project name or metadata of the project of destination project
    :type destination_project: str or dict
    :param include_annotations: enables annotations copy
    :type include_annotations: bool
    :param copy_annotation_status: enables annotations status copy
    :type copy_annotation_status: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    """
    source_project, source_project_folder = get_project_and_folder_metadata(
        source_project
    )
    destination_project, destination_project_folder = get_project_and_folder_metadata(
        destination_project
    )
    img_b = get_image_bytes((source_project, source_project_folder), image_name)
    new_name = image_name
    extension = Path(image_name).suffix
    p = re.compile(r"_\([0-9]+\)\.")
    while True:
        try:
            get_image_metadata(
                (destination_project, destination_project_folder), new_name
            )
        except SABaseException:
            break
        else:
            for m in p.finditer(new_name):
                if m.start() + len(m.group()
                                  ) + len(extension) - 1 == len(new_name):
                    num = int(m.group()[2:-2])
                    new_name = new_name[:m.start() +
                                        2] + str(num + 1) + ")" + extension
                    break
            else:
                new_name = Path(new_name).stem + "_(1)" + extension

    upload_image_to_project(
        (destination_project, destination_project_folder), img_b, new_name
    )
    _copy_annotations_and_metadata(
        source_project, source_project_folder, image_name, destination_project,
        destination_project_folder, new_name, include_annotations,
        copy_annotation_status, copy_pin
    )
    logger.info(
        "Copied image %s/%s to %s/%s.", source_project["name"], image_name,
        destination_project["name"], new_name
    )


def _copy_annotations_and_metadata(
    source_project, source_project_folder, image_name, destination_project,
    destination_project_folder, new_name, include_annotations,
    copy_annotation_status, copy_pin
):
    if include_annotations:
        annotations = get_image_annotations(
            (source_project, source_project_folder), image_name
        )
        if annotations["annotation_json"] is not None:
            if "annotation_mask" in annotations:
                if annotations["annotation_mask"] is not None:
                    upload_image_annotations(
                        (destination_project, destination_project_folder),
                        new_name, annotations["annotation_json"],
                        annotations["annotation_mask"]
                    )
            else:
                upload_image_annotations(
                    (destination_project, destination_project_folder), new_name,
                    annotations["annotation_json"]
                )
    if copy_annotation_status or copy_pin:
        img_metadata = get_image_metadata(
            (source_project, source_project_folder), image_name
        )
        if copy_annotation_status:
            set_image_annotation_status(
                (destination_project, destination_project_folder), new_name,
                img_metadata["annotation_status"]
            )
        if copy_pin:
            pin_image(
                (destination_project, destination_project_folder), new_name,
                img_metadata["is_pinned"]
            )


def move_image(
    source_project,
    image_name,
    destination_project,
    include_annotations=True,
    copy_annotation_status=True,
    copy_pin=True
):
    """Move image from source_project to destination_project. source_project
    and destination_project cannot be the same.

    :param source_project: project name or metadata of the project of source project
    :type source_project: str or dict
    :param image_name: image name
    :type image: str
    :param destination_project: project name or metadata of the project of destination project
    :type destination_project: str or dict
    :param include_annotations: enables annotations move
    :type include_annotations: bool
    :param copy_annotation_status: enables annotations status copy
    :type copy_annotation_status: bool
    :param copy_pin: enables image pin status copy
    :type copy_pin: bool
    """
    source_project, source_project_folder = get_project_and_folder_metadata(
        source_project
    )
    destination_project, destination_project_folder = get_project_and_folder_metadata(
        destination_project
    )
    if source_project == destination_project:
        raise SABaseException(
            0, "Cannot move image if source_project == destination_project."
        )
    copy_image(
        (source_project, source_project_folder), image_name,
        (destination_project, destination_project_folder), include_annotations,
        copy_annotation_status, copy_pin
    )
    delete_image((source_project, source_project_folder), image_name)
    logger.info("Deleted image %s/%s.", source_project["name"], image_name)


def pin_image(project, image_name, pin=True):
    """Pins (or unpins) image

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_name: image name
    :type image: str
    :param pin: sets to pin if True, else unpins image
    :type pin: bool
    """
    project, project_folder = get_project_and_folder_metadata(project)
    img_metadata = get_image_metadata((project, project_folder), image_name)
    team_id, project_id, image_id = project["team_id"], project[
        "id"], img_metadata["id"]
    params = {"team_id": team_id, "project_id": project_id}
    if project_folder is not None:
        params["folder_id"] = project_folder["id"]
    json_req = {"is_pinned": int(pin)}
    response = _api.send_request(
        req_type='PUT',
        path=f'/image/{image_id}',
        params=params,
        json_req=json_req
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't pin image " + response.text
        )


def assign_images(project, image_names, user):
    """Assigns images to a user. The assignment role, QA or Annotator, will
    be deduced from the user's role in the project. With SDK, the user can be
    assigned to a role in the project with the share_project function.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param image_names: list of image names to assign
    :type image_names: list of str
    :param user: user email
    :type user: str
    """
    logger.info("Assign %s images to user %s", len(image_names), user)
    if len(image_names) == 0:
        return
    project, project_folder = get_project_and_folder_metadata(project)
    images = search_images((project, project_folder), return_metadata=True)
    image_dict = {}
    for image in images:
        image_dict[image["name"]] = image["id"]

    image_ids = []
    for image_name in image_names:
        image_ids.append(image_dict[image_name])
    team_id, project_id = project["team_id"], project["id"]
    params = {"team_id": team_id, "project_id": project_id}
    if project_folder is not None:
        params['folder_id'] = project_folder['id']
    json_req = {"user_id": user, "image_ids": image_ids}
    response = _api.send_request(
        req_type='POST',
        path='/images/assign',
        params=params,
        json_req=json_req
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't assign images " + response.text
        )
