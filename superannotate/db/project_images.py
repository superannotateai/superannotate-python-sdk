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
    search_images, set_image_annotation_status, upload_image_annotations
)
from .project_api import get_project_metadata_bare
from .projects import (
    __create_image, get_project_default_image_quality_in_editor,
    get_image_array_to_upload, upload_image_array_to_s3
)

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

    :param project: project name or metadata of the project to upload image to
    :type project: str or dict
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
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
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
        raise SAImageSizeTooLarge(file_size)

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
    key = prefix + f'{img_name}'
    try:
        images_array = get_image_array_to_upload(
            img, image_quality_in_editor, project["type"]
        )
        upload_image_array_to_s3(bucket, *images_array, key, project["type"])
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

    :param source_project: project name or metadata of the project of source project
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
    if not isinstance(source_project, dict):
        source_project = get_project_metadata_bare(source_project)
    if not isinstance(destination_project, dict):
        destination_project = get_project_metadata_bare(destination_project)
    img_b = get_image_bytes(source_project, image_name)
    img_metadata = get_image_metadata(source_project, image_name)
    new_name = image_name
    extension = Path(image_name).suffix
    p = re.compile(r"_\([0-9]+\)\.")
    while True:
        try:
            get_image_metadata(destination_project, new_name)
        except SABaseException:
            break
        else:
            found_copied = False
            for m in p.finditer(new_name):
                if m.start() + len(m.group()
                                  ) + len(extension) - 1 == len(new_name):
                    num = int(m.group()[2:-2])
                    found_copied = True
                    break
            if not found_copied:
                new_name = Path(new_name).stem + "_(1)" + extension
            else:
                new_name = new_name[:m.start() +
                                    2] + str(num + 1) + ")" + extension
    upload_image_to_project(destination_project, img_b, new_name)
    if include_annotations:
        annotations = get_image_annotations(source_project, image_name)
        if annotations["annotation_json"] is not None:
            if "annotation_mask" in annotations:
                upload_image_annotations(
                    destination_project, new_name,
                    annotations["annotation_json"],
                    annotations["annotation_mask"]
                )
            else:
                upload_image_annotations(
                    destination_project, new_name,
                    annotations["annotation_json"]
                )
    if copy_annotation_status:
        set_image_annotation_status(
            destination_project, new_name, img_metadata["annotation_status"]
        )
    if copy_pin:
        pin_image(destination_project, new_name, img_metadata["is_pinned"])

    logger.info(
        "Copied image %s/%s to %s/%s.", source_project["name"], image_name,
        destination_project["name"], new_name
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
    if not isinstance(source_project, dict):
        source_project = get_project_metadata_bare(source_project)
    if not isinstance(destination_project, dict):
        destination_project = get_project_metadata_bare(destination_project)
    if source_project == destination_project:
        raise SABaseException(
            0, "Cannot move image if source_project == destination_project."
        )
    copy_image(
        source_project, image_name, destination_project, include_annotations,
        copy_annotation_status, copy_pin
    )
    delete_image(source_project, image_name)
    logger.info("Deleted image %s/%s.", source_project["name"], image_name)


def pin_image(project, image_name, pin=True):
    """Pins (or unpins) image

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_name: image name
    :type image: str
    :param pin: sets to pin if True, else unpins image
    :type pin: bool
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    img_metadata = get_image_metadata(project, image_name)
    team_id, project_id, image_id = project["team_id"], project[
        "id"], img_metadata["id"]
    params = {"team_id": team_id, "project_id": project_id}
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

    :param project: project name or metadata of the project
    :type project: str or dict
    :param image_names: list of image names to assign
    :type image_names: list of str
    :param user: user email
    :type user: str
    """
    logger.info("Assign %s images to user %s", len(image_names), user)
    if len(image_names) == 0:
        return
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    folder_id = None
    images = search_images(project, return_metadata=True)
    image_dict = {}
    for image in images:
        image_dict[image["name"]] = image["id"]
        if folder_id is None:
            folder_id = image["folder_id"]
        elif folder_id != image["folder_id"]:
            raise SABaseException(0, "Folders not implemented yet")

    image_ids = []
    for image_name in image_names:
        image_ids.append(image_dict[image_name])
    team_id, project_id = project["team_id"], project["id"]
    params = {
        "team_id": team_id,
        "project_id": project_id,
        "folder_id": folder_id
    }
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
    # print(response.json())
