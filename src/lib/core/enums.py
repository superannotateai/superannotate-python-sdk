from enum import Enum
from types import DynamicClassAttribute


class BaseTitledEnum(Enum):
    @DynamicClassAttribute
    def name(self):
        return super().value[0]

    @DynamicClassAttribute
    def value(self):
        return super().name[1]


class ProjectType(Enum):
    VECTOR = 1
    PIXEL = 2


class UserRole(Enum):
    ADMIN = 2
    ANNOTATOR = 3
    QA = 4
    CUSTOMER = 5
    VIEWER = 6


class UploadState(Enum):
    INITIAL = 1
    BASIC = 2
    EXTERNAL = 3


class TrainingStatus(BaseTitledEnum):
    NOT_STARTED = "NotStarted", 1
    IN_PROGRESS = "InProgress", 2
    COMPLETED = "Completed", 3
    FAILED_BEFORE_EVALUATION = "FailedBeforeEvaluation", 4
    FAILED_AFTER_EVALUATION = "FailedAfterEvaluation", 5


class SegmentationStatus(BaseTitledEnum):
    NOT_STARTED = "NotStarted", 1
    IN_PROGRESS = "InProgress", 2
    COMPLETED = "Completed", 3
    FAILED = "Failed", 4


class TrainingTask(BaseTitledEnum):
    INSTANCE_SEGMENTATION_PIXEL = (
        "Instance Segmentation for Pixel Projects",
        "instance_segmentation_pixel",
    )
    INSTANCE_SEGMENTATION_VECTOR = (
        "Instance Segmentation for Vector Projects",
        "instance_segmentation_vector",
    )
    KEYPOINT_DETECTION_VECTOR = (
        "Keypoint Detection for Vector Projects",
        "keypoint_detection_vector",
    )
    OBJECT_DETECTION_VECTOR = (
        "Object Detection for Vector Projects",
        "object_detection_vector",
    )
    SEMANTIC_SEGMENTATION_PIXEL = (
        "Semantic Segmentation for Pixel Projects",
        "semantic_segmentation_pixel",
    )
