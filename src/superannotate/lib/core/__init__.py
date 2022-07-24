from os.path import expanduser

from superannotate.lib.core.config import Config
from superannotate.lib.core.enums import AnnotationStatus
from superannotate.lib.core.enums import ImageQuality
from superannotate.lib.core.enums import ProjectState
from superannotate.lib.core.enums import ProjectStatus
from superannotate.lib.core.enums import ProjectType
from superannotate.lib.core.enums import SegmentationStatus
from superannotate.lib.core.enums import TrainingStatus
from superannotate.lib.core.enums import TrainingTask
from superannotate.lib.core.enums import UploadState
from superannotate.lib.core.enums import UserRole

CONFIG = Config()

CONFIG_PATH = "~/.superannotate/config.json"
CONFIG_FILE_LOCATION = expanduser(CONFIG_PATH)
LOG_FILE_LOCATION = expanduser("~/.superannotate/sa.log")
BACKEND_URL = "https://api.annotate.online"

DEFAULT_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp"]
DEFAULT_FILE_EXCLUDE_PATTERNS = ["___save.png", "___fuse.png"]
DEFAULT_VIDEO_EXTENSIONS = ["mp4", "avi", "mov", "webm", "flv", "mpg", "ogg"]
DEFAULT_HYPER_PARAMETERS = {
    "instance_type": "1 x T4 16 GB",
    "num_epochs": 12,
    "dataset_split_ratio": 80,
    "base_lr": 0.02,
    "gamma": 0.5,
    "images_per_batch": 4,
    "batch_per_image": 512,
    "steps": [5],
    "evaluation_period": 12,
    "runtime_seconds": 600,
    "estimated_remaining_time": 600,
    "template_id": None,
}

MODEL_TRAINING_TASKS = {
    "Instance Segmentation for Pixel Projects": "instance_segmentation_pixel",
    "Instance Segmentation for Vector Projects": "instance_segmentation_vector",
    "Keypoint Detection for Vector Projects": "keypoint_detection_vector",
    "Object Detection for Vector Projects": "object_detection_vector",
    "Semantic Segmentation for Pixel Projects": "semantic_segmentation_pixel",
}

AVAILABLE_SEGMENTATION_MODELS = ["autonomous", "generic"]

VECTOR_ANNOTATION_POSTFIX = "___objects.json"
PIXEL_ANNOTATION_POSTFIX = "___pixel.json"
ANNOTATION_MASK_POSTFIX = "___save.png"
ATTACHED_VIDEO_ANNOTATION_POSTFIX = ".json"

NON_PLOTABLE_KEYS = ["eta_seconds", "iteration", "data_time", "time", "model"]

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

LIMITED_FUNCTIONS = {
    ProjectType.VIDEO.value: DEPRECATED_VIDEO_PROJECTS_MESSAGE,
    ProjectType.DOCUMENT.value: DEPRECATED_DOCUMENT_PROJECTS_MESSAGE,
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

__alL__ = (
    ProjectState,
    ProjectStatus,
    ProjectType,
    UserRole,
    UploadState,
    TrainingStatus,
    SegmentationStatus,
    TrainingTask,
    ImageQuality,
    AnnotationStatus,
    CONFIG_FILE_LOCATION,
    CONFIG_PATH,
    BACKEND_URL,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_FILE_EXCLUDE_PATTERNS,
    DEFAULT_VIDEO_EXTENSIONS,
    MAX_IMAGE_SIZE,
    MAX_VECTOR_RESOLUTION,
    MAX_PIXEL_RESOLUTION,
)
