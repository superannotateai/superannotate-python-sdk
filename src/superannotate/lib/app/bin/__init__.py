DEFAULT_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp")

DEFAULT_FILE_EXCLUDE_PATTERNS = ("___save.png", "___fuse.png")

DEFAULT_VIDEO_EXTENSIONS = ("mp4", "avi", "mov", "webm", "flv", "mpg", "ogg")

SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES = set('/\\:*?"<>|')

_PROJECT_TYPES = {"Vector": 1, "Pixel": 2}

_ANNOTATION_STATUSES = {
    "NotStarted": 1,
    "InProgress": 2,
    "QualityCheck": 3,
    "Returned": 4,
    "Completed": 5,
    "Skipped": 6,
}

UPLOAD_STATES_STR_TO_CODES = {"Initial": 1, "Basic": 2, "External": 3}
UPLOAD_STATES_CODES_TO_STR = {1: "Initial", 2: "Basic", 3: "External"}

USER_ROLES = {"Admin": 2, "Annotator": 3, "QA": 4, "Customer": 5, "Viewer": 6}
AVAILABLE_SEGMENTATION_MODELS = ["autonomous", "generic"]
MODEL_TRAINING_STATUSES = {
    "NotStarted": 1,
    "InProgress": 2,
    "Completed": 3,
    "FailedBeforeEvaluation": 4,
    "FailedAfterEvaluation": 5,
    "FailedAfterEvaluationWithSavedModel": 6,
}

PREDICTION_SEGMENTATION_STATUSES = {
    "NotStarted": 1,
    "InProgress": 2,
    "Completed": 3,
    "Failed": 4,
}

MODEL_TRAINING_TASKS = {
    "Instance Segmentation for Pixel Projects": "instance_segmentation_pixel",
    "Instance Segmentation for Vector Projects": "instance_segmentation_vector",
    "Keypoint Detection for Vector Projects": "keypoint_detection_vector",
    "Object Detection for Vector Projects": "object_detection_vector",
    "Semantic Segmentation for Pixel Projects": "semantic_segmentation_pixel",
}
