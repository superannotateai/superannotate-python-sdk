import logging
import math
from pathlib import Path
import zipfile
import time
from datetime import datetime
import tempfile
import threading

import requests
import boto3
from tqdm import tqdm

from ..api import API
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()
_NUM_THREADS = 10


def get_exports(project):
    """Get all exports of the project
    Returns
    -------
    list:
        list of dict objects representing exports
    """
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': team_id, 'project_id': project_id}
    response = _api.send_request(req_type='GET', path='/exports', params=params)
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get exports. " + response.text
        )
    return response.json()


def get_export(export):
    """Get export object of the project
    Returns
    -------
    dict:
        dict object representing exports
    """
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
    project, include_images_with_status=None, include_fuse=1, only_pinned=0
):
    """Prepare export of the project
    Returns
    -------
    dict:
        dict representing the created export
    """
    team_id, project_id = project["team_id"], project["id"]
    if include_images_with_status is None:
        include_images_with_status = [2, 3, 4, 5]
    include_images_with_status = [str(x) for x in include_images_with_status]
    include_images_with_status = ",".join(include_images_with_status)
    current_time = datetime.now().strftime("%b %d %Y %H:%M")
    json_req = {
        "include": include_images_with_status,
        "fuse": include_fuse,
        "is_pinned": only_pinned,
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
    return response.json()


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
            s3_key = f'{folder_path}/{relative_filename}'
            to_s3.upload_file(str(file), s3_key)
        except Exception as e:
            logger.warning("Unable to upload to data server %s", e)
            return
        else:
            num_uploaded[thread_id] += 1
            already_uploaded[i] = True


def download_export(
    export, folder_path, extract_zip_contents=True, to_s3_bucket=None
):
    """Download export
    Returns
    -------
    None
    """
    while True:
        res = get_export(export)
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
            for file in Path(tmpdirname).rglob("*"):
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
