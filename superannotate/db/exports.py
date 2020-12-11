import logging
import math
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

import boto3
import requests
from tqdm import tqdm

from ..api import API
from ..common import annotation_status_str_to_int
from ..exceptions import (
    SABaseException, SAExistingExportNameException,
    SANonExistingExportNameException
)
from .project_api import get_project_metadata_bare

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()
_NUM_THREADS = 10


def get_export_metadata(project, export_name):
    """Returns project metadata

    :param project: project name or metadata of the project
    :type project: str or dict
    :param export_name: export name
    :type project: str

    :return: metadata of export
    :rtype: dict
    """
    exports = get_exports(project, return_metadata=True)
    results = []
    for export in exports:
        if export["name"] == export_name:
            results.append(export)

    if len(results) == 0:
        raise SANonExistingExportNameException(
            0, "Export with name " + export_name + " doesn't exist."
        )
    elif len(results) == 1:
        return results[0]
    else:
        raise SAExistingExportNameException(
            0, "Export name " + export_name +
            " is not unique. To use SDK please use unique export names."
        )


def get_exports(project, return_metadata=False):
    """Get all prepared exports of the project.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param return_metadata: return metadata of images instead of names
    :type return_metadata: bool

    :return: names or metadata objects of the all prepared exports of the project
    :rtype: list of strs or dicts
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': team_id, 'project_id': project_id}
    response = _api.send_request(req_type='GET', path='/exports', params=params)
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get exports. " + response.text
        )
    res = response.json()
    if return_metadata:
        return res
    else:
        return [x["name"] for x in res]


def _get_export(export):
    team_id, project_id, export_id = export["team_id"], export["project_id"
                                                              ], export["id"]
    params = {'team_id': team_id, 'project_id': project_id}
    response = _api.send_request(
        req_type='GET', path=f'/export/{export_id}', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get export. " + response.text
        )
    return response.json()


def prepare_export(
    project, annotation_statuses=None, include_fuse=False, only_pinned=False
):
    """Prepare annotations and classes.json for export. Original and fused images for images with
    annotations can be included with include_fuse flag.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param annotation_statuses: images with which status to include, if None, [ "InProgress", "QualityCheck", "Returned", "Completed"] will be chose
           list elements should be one of NotStarted InProgress QualityCheck Returned Completed Skipped
    :type annotation_statuses: list of strs
    :param include_fuse: enables fuse images in the export
    :type include_fuse: bool
    :param only_pinned: enable only pinned output in export. This option disables all other types of output.
    :type only_pinned: bool

    :return: metadata object of the prepared export
    :rtype: dict
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    team_id, project_id = project["team_id"], project["id"]
    if annotation_statuses is None:
        annotation_statuses = [2, 3, 4, 5]
    else:
        int_list = map(annotation_status_str_to_int, annotation_statuses)
        annotation_statuses = int_list
    annotation_statuses = [str(x) for x in annotation_statuses]
    annotation_statuses = ",".join(annotation_statuses)
    current_time = datetime.now().strftime("%b %d %Y %H:%M")
    json_req = {
        "include": annotation_statuses,
        "fuse": int(include_fuse),
        "is_pinned": int(only_pinned),
        "coco": 0,
        "time": current_time
    }
    params = {'team_id': team_id, 'project_id': project_id}
    response = _api.send_request(
        req_type='POST', path='/export', params=params, json_req=json_req
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't create_export." + response.text
        )
    res = response.json()
    logger.info(
        "Prepared export %s for project %s (ID %s).", res['name'],
        project["name"], project["id"]
    )
    return res


def __tqdm_thread(total_num, current_nums, finish_event):
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(5)
            if not finished:
                pbar.update(sum(current_nums) - pbar.n)
            else:
                pbar.update(total_num - pbar.n)
                break


def __upload_files_to_aws_thread(
    to_s3_bucket,
    folder_path,
    filepaths,
    tmpdirname,
    thread_id,
    chunksize,
    already_uploaded,
    num_uploaded,
):
    len_files_to_upload = len(filepaths)
    start_index = thread_id * chunksize
    end_index = start_index + chunksize
    if start_index >= len_files_to_upload:
        return
    to_s3 = boto3.Session().resource('s3').Bucket(to_s3_bucket)
    for i in range(start_index, end_index):
        if i >= len_files_to_upload:
            break
        if already_uploaded[i]:
            continue
        file = filepaths[i]
        try:
            relative_filename = file.relative_to(tmpdirname)
            s3_key = f'{folder_path}/{relative_filename.as_posix()}'
            to_s3.upload_file(str(file), s3_key)
        except Exception as e:
            logger.warning("Unable to upload to data server %s", e)
            return
        else:
            num_uploaded[thread_id] += 1
            already_uploaded[i] = True


def download_export(
    project, export, folder_path, extract_zip_contents=True, to_s3_bucket=None
):
    """Download prepared export.

    WARNING: Starting from version 1.9.0 :ref:`download_export <ref_download_export>` additionally
    requires :py:obj:`project` as first argument.

    :param project: project name or metadata of the project
    :type project: str or dict
    :param export: export name or metadata of the prepared export
    :type export: str or dict
    :param folder_path: where to download the export
    :type folder_path: Pathlike (str or Path)
    :param extract_zip_contents: if False then a zip file will be downloaded,
     if True the zip file will be extracted at folder_path
    :type extract_zip_contents: bool
    :param to_s3_bucket: AWS S3 bucket to use for download. If None then folder_path is in local filesystem.
    :type tofrom_s3_bucket: str
    """
    if not isinstance(export, dict):
        export = get_export_metadata(project, export)

    while True:
        res = _get_export(export)
        if res["status"] == 1:
            logger.info("Waiting 5 seconds for export to finish on server.")
            time.sleep(5)
            continue
        if res["status"] == 4:
            raise SABaseException(0, "Couldn't download export.")
        break

    filename = Path(res['path']).name
    r = requests.get(res['download'], allow_redirects=True)
    if to_s3_bucket is None:
        filepath = Path(folder_path) / filename
        open(filepath, 'wb').write(r.content)
        if extract_zip_contents:
            with zipfile.ZipFile(filepath, 'r') as f:
                f.extractall(folder_path)
            Path.unlink(filepath)
            logger.info("Extracted %s to folder %s", filepath, folder_path)
        else:
            logger.info("Downloaded export ID %s to %s", res['id'], filepath)
    else:
        with tempfile.TemporaryDirectory() as tmpdirname:
            filepath = Path(tmpdirname) / filename
            open(filepath, 'wb').write(r.content)
            if extract_zip_contents:
                with zipfile.ZipFile(filepath, 'r') as f:
                    f.extractall(tmpdirname)
                Path.unlink(filepath)
            files_to_upload = []
            for file in Path(tmpdirname).rglob("*.*"):
                if not file.is_file():
                    continue
                files_to_upload.append(file)
            len_files_to_upload = len(files_to_upload)
            num_uploaded = [0] * _NUM_THREADS
            already_uploaded = [False] * len_files_to_upload
            finish_event = threading.Event()
            chunksize = int(math.ceil(len_files_to_upload / _NUM_THREADS))
            tqdm_thread = threading.Thread(
                target=__tqdm_thread,
                args=(len_files_to_upload, num_uploaded, finish_event)
            )
            tqdm_thread.start()
            while True:
                if sum(num_uploaded) == len_files_to_upload:
                    break
                threads = []
                for thread_id in range(_NUM_THREADS):
                    t = threading.Thread(
                        target=__upload_files_to_aws_thread,
                        args=(
                            to_s3_bucket, folder_path, files_to_upload,
                            tmpdirname, thread_id, chunksize, already_uploaded,
                            num_uploaded
                        )
                    )
                    threads.append(t)
                    t.start()
                for t in threads:
                    t.join()
            finish_event.set()
            tqdm_thread.join()
        logger.info("Exported to AWS %s/%s", to_s3_bucket, folder_path)
