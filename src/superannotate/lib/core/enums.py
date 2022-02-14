from enum import Enum
from types import DynamicClassAttribute


class BaseTitledEnum(Enum):
    @DynamicClassAttribute
    def name(self) -> str:
        return super().value[0]

    @DynamicClassAttribute
    def value(self):
        return super().value[1]

    @classmethod
    def get_name(cls, value):
        for enum in list(cls):
            if enum.value == value:
                return enum.name

    @classmethod
    def get_value(cls, name):
        for enum in list(cls):
            if enum.name.lower() == name.lower():
                return enum.value

    @classmethod
    def values(cls):
        return [enum.name.lower() for enum in list(cls)]

    @classmethod
    def titles(cls):
        return [enum.name for enum in list(cls)]

    def equals(self, other: Enum):
        return self.name.lower() == other.lower()


class ProjectType(BaseTitledEnum):
    VECTOR = "Vector", 1
    PIXEL = "Pixel", 2
    VIDEO = "Video", 3
    DOCUMENT = "Document", 4


class UserRole(BaseTitledEnum):
    SUPER_ADMIN = "Superadmin", 1
    ADMIN = "Admin", 2
    ANNOTATOR = "Annotator", 3
    QA = "QA", 4
    CUSTOMER = "Customer", 5
    VIEWER = "Viewer", 6


class UploadState(Enum):
    INITIAL = 1
    BASIC = 2
    EXTERNAL = 3


class ImageQuality(BaseTitledEnum):
    ORIGINAl = "original", 100
    COMPRESSED = "compressed", 60


class ExportStatus(BaseTitledEnum):
    IN_PROGRESS = "inProgress", 1
    COMPLETE = "complete", 2
    CANCELED = "canceled", 3
    ERROR = "error", 4


class AnnotationStatus(BaseTitledEnum):
    NOT_STARTED = "NotStarted", 1
    IN_PROGRESS = "InProgress", 2
    QUALITY_CHECK = "QualityCheck", 3
    RETURNED = "Returned", 4
    COMPLETED = "Completed", 5
    SKIPPED = "Skipped", 6


class ClassTypeEnum(BaseTitledEnum):
    OBJECT = "object", 1
    TAG = "tag", 2


class TrainingStatus(BaseTitledEnum):
    NOT_STARTED = "NotStarted", 1
    IN_PROGRESS = "InProgress", 2
    COMPLETED = "Completed", 3
    FAILED_BEFORE_EVALUATION = "FailedBeforeEvaluation", 4
    FAILED_AFTER_EVALUATION = "FailedAfterEvaluation", 5
    FAILED_AFTER_EVALUATION_WITH_SAVE_MODEL = "FailedAfterEvaluationWithSavedModel", 6


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
