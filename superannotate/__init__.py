import logging

from .api import API

from .version import Version

from .common import image_path_to_annotation_paths

from .db.exports import get_exports, download_export, prepare_export
from .db.users import search_users
from .db.teams import search_teams, get_default_team, create_team, delete_team
from .db.images import search_images, set_image_annotation_status, download_image, download_image_annotations, get_image_bytes, get_image_annotations, upload_annotations_from_file_to_image, get_image, get_image_preannotations, download_image_preannotations
from .db.projects import search_projects, create_project, upload_images_from_folder, get_root_folder_id, upload_annotations_from_folder, get_project_type, upload_preannotations_from_folder, share_project, unshare_project, delete_project, get_project_image_count, get_project, upload_from_s3_bucket, get_upload_from_s3_bucket_status
from .db.project_classes import search_classes, create_class, create_classes_from_classes_json, download_classes_json

from .exceptions import SABaseException

#formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
formatter = logging.Formatter(fmt='sa-PYTHON-SDK - %(levelname)s - %(message)s')

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger("annotateonline-python-sdk")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

_api = API.get_instance()


def init(path_to_config_json):
    """Authenticates to Superannotate platform using the config file.

    :param path_to_config_json: Location to config JSON
    :type path_to_config_json:
    """
    _api.set_auth(path_to_config_json)
