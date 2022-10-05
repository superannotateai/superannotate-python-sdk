from enum import Enum
from types import DynamicClassAttribute


class classproperty:
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class BaseTitledEnum(int, Enum):
    def __new__(cls, title, value):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.__doc__ = title
        obj._type = "titled_enum"
        cls._value2member_map_[title] = obj
        return obj

    @classmethod
    def choices(cls):
        return tuple(cls._value2member_map_.keys())

    @DynamicClassAttribute
    def name(self) -> str:
        return self.__doc__

    @DynamicClassAttribute
    def value(self):
        return super().value

    @classmethod
    def get_name(cls, value):
        for enum in list(cls):
            if enum.value == value:
                return enum.__doc__

    @classmethod
    def get_value(cls, name):
        for enum in list(cls):
            if enum.__doc__.lower() == name.lower():
                return enum.value

    @classmethod
    def values(cls):
        return [enum.__doc__.lower() for enum in list(cls)]

    @classmethod
    def titles(cls):
        return [enum.__doc__ for enum in list(cls)]

    def equals(self, other: Enum):
        return self.__doc__.lower() == other.__doc__.lower()

    def __eq__(self, other):
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.name)


class AnnotationTypes(str, Enum):
    BBOX = "bbox"
    EVENT = "event"
    POINT = "point"
    POLYGON = "polygon"
    POLYLINE = "polyline"


class ProjectType(BaseTitledEnum):
    VECTOR = "Vector", 1
    PIXEL = "Pixel", 2
    VIDEO = "Video", 3
    DOCUMENT = "Document", 4

    @classproperty
    def images(self):
        return self.VECTOR.value, self.PIXEL.value


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


class ProjectStatus(BaseTitledEnum):
    Undefined = "Undefined", 0
    NotStarted = "NotStarted", 1
    InProgress = "InProgress", 2
    Completed = "Completed", 3
    OnHold = "OnHold", 4


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

    @classmethod
    def get_value(cls, name):
        for enum in list(cls):
            if enum.__doc__.lower() == name.lower():
                return enum.value
        return cls.OBJECT.value


class IntegrationTypeEnum(BaseTitledEnum):
    AWS = "aws", 1
    GCP = "gcp", 2
    AZURE = "azure", 3


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


class ApprovalStatus(BaseTitledEnum):
    NONE = None, 0
    DISAPPROVED = "disapproved", 1
    APPROVED = "approved", 2
