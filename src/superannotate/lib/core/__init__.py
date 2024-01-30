import logging
import os
from logging import Formatter
from logging.handlers import RotatingFileHandler
from os.path import expanduser

from lib.core.config import Config
from lib.core.enums import AnnotationStatus
from lib.core.enums import ApprovalStatus
from lib.core.enums import FolderStatus
from lib.core.enums import ImageQuality
from lib.core.enums import ProjectStatus
from lib.core.enums import ProjectType
from lib.core.enums import SegmentationStatus
from lib.core.enums import TrainingStatus
from lib.core.enums import UploadState
from lib.core.enums import UserRole

CONFIG = Config()
BACKEND_URL = "https://api.superannotate.com"
HOME_PATH = expanduser("~/.superannotate")

CONFIG_JSON_PATH = f"{HOME_PATH}/config.json"
CONFIG_INI_PATH = f"{HOME_PATH}/config.ini"
CONFIG_JSON_FILE_LOCATION = CONFIG_JSON_PATH
CONFIG_INI_FILE_LOCATION = CONFIG_INI_PATH

LOG_FILE_LOCATION = f"{HOME_PATH}/logs"
DEFAULT_LOGGING_LEVEL = "INFO"

_loggers = {}


def setup_logging(level=DEFAULT_LOGGING_LEVEL, file_path=LOG_FILE_LOCATION):
    logger = logging.getLogger("sa")
    for handler in logger.handlers[:]:  # remove all old handlers
        logger.removeHandler(handler)
    logger.propagate = False
    logger.setLevel(level)
    stream_handler = logging.StreamHandler()
    formatter = Formatter("SA-PYTHON-SDK - %(levelname)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    try:
        os.makedirs(file_path, exist_ok=True)
        log_file_path = os.path.join(file_path, "sa.log")
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            mode="a",
        )
        file_formatter = Formatter(
            "SA-PYTHON-SDK - %(levelname)s - %(asctime)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    except OSError as e:
        logger.debug(e)


DEFAULT_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp"]
DEFAULT_FILE_EXCLUDE_PATTERNS = ["___save.png", "___fuse.png"]
DEFAULT_VIDEO_EXTENSIONS = ["mp4", "avi", "mov", "webm", "flv", "mpg", "ogg"]

VECTOR_ANNOTATION_POSTFIX = "___objects.json"
PIXEL_ANNOTATION_POSTFIX = "___pixel.json"
ANNOTATION_MASK_POSTFIX = "___save.png"
ATTACHED_VIDEO_ANNOTATION_POSTFIX = ".json"

SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES = set('/\\:*?"<>|“')
MAX_PIXEL_RESOLUTION = 4_000_000
MAX_VECTOR_RESOLUTION = 100_000_000
MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100 MB limit
TOKEN_UUID = "token"

ALREADY_EXISTING_FILES_WARNING = (
    "{} already existing file(s) found that won't be uploaded."
)

ATTACHING_FILES_MESSAGE = "Attaching {} file(s) to project {}."

ATTACHING_UPLOAD_STATE_ERROR = "You cannot attach URLs in this type of project. Please attach it in an external storage project."
UPLOADING_UPLOAD_STATE_ERROR = "You cannot upload files in this type of project. Please upload it in an basic storage project."

INVALID_PROJECT_TYPE_TO_PROCESS = "The function does not support projects of type {}."
DEPRECATED_VIDEO_PROJECTS_MESSAGE = (
    "The function does not support projects containing videos attached with URLs"
)

DEPRECATED_DOCUMENT_PROJECTS_MESSAGE = (
    "The function does not support projects containing documents attached with URLs"
)
DEPRECATED_PROJECTS_MESSAGE = (
    "The function does not support projects containing items attached with URLs"
)

LIMITED_FUNCTIONS = {
    ProjectType.VIDEO: DEPRECATED_VIDEO_PROJECTS_MESSAGE,
    ProjectType.DOCUMENT: DEPRECATED_DOCUMENT_PROJECTS_MESSAGE,
    ProjectType.POINT_CLOUD: DEPRECATED_PROJECTS_MESSAGE,
    ProjectType.TILED: DEPRECATED_PROJECTS_MESSAGE,
}

METADATA_DEPRICATED_FOR_PIXEL = (
    "custom_metadata field is not supported for project type Pixel."
)
DEPRICATED_DOCUMENT_VIDEO_MESSAGE = "The function does not support projects containing videos / documents attached with URLs"

UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE = "The number of items you want to upload exceeds the limit of 50 000 items per folder."
UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE = "The number of items you want to upload exceeds the limit of 500 000 items per project."
UPLOAD_USER_LIMIT_ERROR_MESSAGE = "The number of items you want to upload exceeds the limit of your subscription plan."

ATTACH_FOLDER_LIMIT_ERROR_MESSAGE = "The number of items you want to attach exceeds the limit of 50 000 items per folder."
ATTACH_PROJECT_LIMIT_ERROR_MESSAGE = "The number of items you want to attach exceeds the limit of 500 000 items per project."
ATTACH_USER_LIMIT_ERROR_MESSAGE = "The number of items you want to attach  exceeds the limit of your subscription plan."

COPY_FOLDER_LIMIT_ERROR_MESSAGE = (
    "The number of items you want to copy exceeds the limit of 50 000 items per folder."
)
COPY_PROJECT_LIMIT_ERROR_MESSAGE = "The number of items you want to copy exceeds the limit of 500 000 items per project."
COPY_SUPER_LIMIT_ERROR_MESSAGE = (
    "The number of items you want to copy exceeds the limit of your subscription plan."
)

MOVE_FOLDER_LIMIT_ERROR_MESSAGE = (
    "The number of items you want to move exceeds the limit of 50 000 items per folder."
)
MOVE_PROJECT_LIMIT_ERROR_MESSAGE = "The number of items you want to move exceeds the limit of 500 000 items per project."

PACKAGE_VERSION_INFO_MESSAGE = (
    "Development version {} of SuperAnnotate SDK is being used."
)

PACKAGE_VERSION_MAJOR_UPGRADE = (
    "There is a major upgrade of SuperAnnotate Python SDK available on PyPI. "
    "We recommend upgrading. Run 'pip install --upgrade superannotate' to "
    "upgrade from your version {} to {}."
)

PACKAGE_VERSION_UPGRADE = (
    "There is a newer version of SuperAnnotate Python SDK available on PyPI."
    " Run 'pip install --upgrade superannotate' to"
    " upgrade from your version {} to {}"
)

USE_VALIDATE_MESSAGE = (
    "Use the validate_annotations function to discover the possible reason(s) for "
    "which an annotation is invalid."
)

INVALID_JSON_MESSAGE = "Invalid json"

PROJECT_SETTINGS_VALID_ATTRIBUTES = [
    "Brightness",
    "Fill",
    "Contrast",
    "ShowLabels",
    "ShowComments",
    "Image",
    "Lines",
    "AnnotatorFinish",
    "PointSize",
    "FontSize",
    "WorkflowEnable",
    "ClassChange",
    "ShowEntropy",
    "UploadImages",
    "DeleteImages",
    "Download",
    "RunPredictions",
    "RunSegmentations",
    "ImageQuality",
    "ImageAutoAssignCount",
    "FrameMode",
    "FrameRate",
    "JumpBackward",
    "JumpForward",
    "UploadFileType",
    "Tokenization",
    "ImageAutoAssignEnable",
]

__alL__ = (
    FolderStatus,
    ProjectStatus,
    ProjectType,
    UserRole,
    UploadState,
    TrainingStatus,
    SegmentationStatus,
    ImageQuality,
    AnnotationStatus,
    ApprovalStatus,
    CONFIG_JSON_FILE_LOCATION,
    CONFIG_INI_FILE_LOCATION,
    BACKEND_URL,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_FILE_EXCLUDE_PATTERNS,
    DEFAULT_VIDEO_EXTENSIONS,
    MAX_IMAGE_SIZE,
    MAX_VECTOR_RESOLUTION,
    MAX_PIXEL_RESOLUTION,
)
