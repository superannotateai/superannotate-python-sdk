from pathlib import Path

from src.lib.core.enums import ProjectType
from src.lib.core.enums import SegmentationStatus
from src.lib.core.enums import TrainingStatus
from src.lib.core.enums import TrainingTask
from src.lib.core.enums import UploadState
from src.lib.core.enums import UserRole


CONFIG_FILE_LOCATION = str(Path.home() / ".superannotate" / "config.json")
BACKEND_URL = "https://api.annotate.online"

DEFAULT_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp")
DEFAULT_FILE_EXCLUDE_PATTERNS = ("___save.png", "___fuse.png")
DEFAULT_VIDEO_EXTENSIONS = ("mp4", "avi", "mov", "webm", "flv", "mpg", "ogg")

__version__ = "?"

__alL_ = (
    ProjectType,
    UserRole,
    UploadState,
    TrainingStatus,
    SegmentationStatus,
    TrainingTask,
    CONFIG_FILE_LOCATION,
    BACKEND_URL,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_FILE_EXCLUDE_PATTERNS,
    DEFAULT_VIDEO_EXTENSIONS,
    __version__,
)
