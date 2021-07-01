import logging

import packaging.version
import requests

from .analytics.class_analytics import (
    attribute_distribution, class_distribution
)
from .analytics.common import aggregate_annotations_as_df, df_to_annotations
from .annotation_helpers import (
    add_annotation_bbox_to_json, add_annotation_comment_to_json,
    add_annotation_cuboid_to_json, add_annotation_ellipse_to_json,
    add_annotation_point_to_json, add_annotation_polygon_to_json,
    add_annotation_polyline_to_json, add_annotation_template_to_json
)
from .api import API as _API
from .common import image_path_to_annotation_paths

try:
    from .consensus_benchmark.benchmark import benchmark
    from .consensus_benchmark.consensus import consensus
except:
    _WARNING_SHAPELY = "To use superannotate.benchmark or superannotate.consensus functions please install shapely package in Anaconda enviornment with # conda install shapely"

    def benchmark(*args, **kwargs):
        raise RuntimeError(_WARNING_SHAPELY)

    def consensus(*args, **kwargs):
        raise RuntimeError(_WARNING_SHAPELY)


from .dataframe_filtering import (
    filter_annotation_instances, filter_images_by_comments,
    filter_images_by_tags
)
from .db.annotation_classes import (
    create_annotation_class, create_annotation_classes_from_classes_json,
    delete_annotation_class, download_annotation_classes_json,
    get_annotation_class_metadata, search_annotation_classes
)
from .db.exports import (
    download_export, get_export_metadata, get_exports, prepare_export
)
from .db.images import (
    add_annotation_bbox_to_image, add_annotation_comment_to_image,
    add_annotation_cuboid_to_image, add_annotation_ellipse_to_image,
    add_annotation_point_to_image, add_annotation_polygon_to_image,
    add_annotation_polyline_to_image, add_annotation_template_to_image,
    create_fuse_image, delete_image, download_image, download_image_annotations,
    download_image_preannotations, get_image_annotations, get_image_bytes,
    get_image_metadata, get_image_preannotations, search_images,
    search_images_all_folders, set_image_annotation_status,
    set_images_annotation_statuses, upload_image_annotations,
    get_project_root_folder_id
)
from .db.project_api import (
    create_folder, delete_folders, get_folder_metadata,
    get_project_and_folder_metadata, rename_folder, search_folders
)
from .db.project_images import (
    assign_images, copy_image, copy_images, delete_images, move_image,
    move_images, pin_image, upload_image_to_project, assign_folder,
    unassign_folder, unassign_images
)
from .db.projects import (
    clone_project, create_project, create_project_from_metadata, delete_project,
    get_project_default_image_quality_in_editor, get_project_image_count,
    get_project_metadata, get_project_settings, get_project_workflow,
    rename_project, set_project_default_image_quality_in_editor,
    set_project_settings, set_project_workflow, share_project, unshare_project,
    upload_annotations_from_folder_to_project,
    upload_images_from_azure_blob_to_project,
    upload_images_from_folder_to_project,
    upload_images_from_google_cloud_to_project,
    upload_images_from_public_urls_to_project,
    upload_images_from_s3_bucket_to_project, upload_images_to_project,
    attach_image_urls_to_project, upload_preannotations_from_folder_to_project,
    upload_video_to_project, upload_videos_from_folder_to_project
)
from .db.search_projects import search_projects
from .db.teams import (
    delete_contributor_to_team_invitation, get_team_metadata,
    invite_contributor_to_team
)
from .db.users import search_team_contributors
from .dicom_converter import dicom_to_rgb_sequence
from .exceptions import (
    SABaseException, SAExistingAnnotationClassNameException,
    SAExistingProjectNameException, SANonExistingAnnotationClassNameException,
    SANonExistingProjectNameException
)
from .input_converters.conversion import (
    coco_split_dataset, convert_json_version, convert_project_type,
    export_annotation, import_annotation
)
from .ml.ml_funcs import (
    delete_model, download_model, plot_model_metrics, run_prediction,
    run_segmentation, run_training, stop_model_training
)
from .ml.ml_models import search_models
from .old_to_new_format_convertor import update_json_format
from .version import __version__

formatter = logging.Formatter(fmt='SA-PYTHON-SDK - %(levelname)s - %(message)s')
#formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger("superannotate-python-sdk")
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def _check_version():
    local_version = packaging.version.parse(__version__)
    if local_version.is_prerelease:
        logger.warning(
            "Development version %s of SuperAnnotate SDK is being used",
            __version__
        )
    req = requests.get('https://pypi.python.org/pypi/superannotate/json')
    if not req.ok:
        return

    # find max version on PyPI
    releases = req.json().get('releases', [])
    pip_version = packaging.version.parse('0')
    for release in releases:
        ver = packaging.version.parse(release)
        if not ver.is_prerelease or local_version.is_prerelease:
            pip_version = max(pip_version, ver)

    if pip_version.major > local_version.major:
        logger.warning(
            "There is a major upgrade of SuperAnnotate Python SDK available on PyPI. We recommend upgrading. Run 'pip install --upgrade superannotate' to upgrade from your version %s to %s.",
            local_version, pip_version
        )
    elif pip_version > local_version:
        logger.info(
            "There is a newer version of SuperAnnotate Python SDK available on PyPI. Run 'pip install --upgrade superannotate' to upgrade from your version %s to %s.",
            local_version, pip_version
        )


_api = _API.get_instance()


def init(path_to_config_json):
    """Initializes and authenticates to SuperAnnotate platform using the config file.
    If not initialized then $HOME/.superannotate/config.json
    will be used.

    :param path_to_config_json: Location to config JSON file
    :type path_to_config_json: str or Path
    """
    _api.init(path_to_config_json)


_check_version()
init(None)
