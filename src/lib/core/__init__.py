from pathlib import Path

from src.lib.core.enums import AnnotationStatus
from src.lib.core.enums import ProjectType
from src.lib.core.enums import SegmentationStatus
from src.lib.core.enums import TrainingStatus
from src.lib.core.enums import TrainingTask
from src.lib.core.enums import UploadState
from src.lib.core.enums import UserRole


CONFIG_FILE_LOCATION = str(Path.home() / ".superannotate" / "config.ini")
# BACKEND_URL = "https://api.annotate.online"
BACKEND_URL = "https://api.devsuperannotate.com"

DEFAULT_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp")
DEFAULT_FILE_EXCLUDE_PATTERNS = ("___save.png", "___fuse.png")
DEFAULT_VIDEO_EXTENSIONS = ("mp4", "avi", "mov", "webm", "flv", "mpg", "ogg")

VECTOR_ANNOTATION_POSTFIX = "___objects.json"
PIXEL_ANNOTATION_POSTFIX = "___pixel.json"
ANNOTATION_MASK_POSTFIX = "___save.png"

SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES = set('/\\:*?"<>|')
MAX_PIXEL_RESOLUTION = 4_000_000
MAX_VECTOR_RESOLUTION = 100_000_000
MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100 MB limit
TOKEN_UUID = "token"




__version__ = "?"

__alL__ = (
    ProjectType,
    UserRole,
    UploadState,
    TrainingStatus,
    SegmentationStatus,
    TrainingTask,
    AnnotationStatus,
    CONFIG_FILE_LOCATION,
    BACKEND_URL,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_FILE_EXCLUDE_PATTERNS,
    DEFAULT_VIDEO_EXTENSIONS,
    MAX_IMAGE_SIZE,
    MAX_VECTOR_RESOLUTION,
    MAX_PIXEL_RESOLUTION,
    __version__,
)
