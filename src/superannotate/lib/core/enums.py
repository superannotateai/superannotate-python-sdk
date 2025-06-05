import typing
from enum import Enum
from types import DynamicClassAttribute


class classproperty:  # noqa
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class BaseTitledEnum(int, Enum):
    def __new__(cls, title, value):
        obj = super().__new__(cls, value)
        obj._value_ = value
        obj.__doc__ = title
        cls._value2member_map_[title] = obj
        return obj

    def __repr__(self):
        return self._name_

    @DynamicClassAttribute
    def name(self) -> str:
        return self.__doc__

    @DynamicClassAttribute
    def value(self) -> int:
        return super().value

    def __unicode__(self):
        return self.__doc__

    @classmethod
    def choices(cls) -> typing.Tuple[str]:
        """Return all titles as choices."""
        return tuple(cls._value2member_map_.keys())

    @property
    def title(self) -> str:
        return self._name_

    @classmethod
    def values(cls) -> typing.List[str]:
        """Return all values (names/titles) in lowercase."""
        return [enum.__doc__.lower() for enum in cls if enum.__doc__]

    @classmethod
    def titles(cls) -> typing.Tuple[str]:
        """Return all titles in the enum."""
        return tuple(enum.__doc__ for enum in cls)

    def equals(self, other: Enum) -> bool:
        """Compare this enum's name/title with another enum's name/title."""
        return (
            self.__doc__.lower() == other.__doc__.lower()
            if self.__doc__ and other.__doc__
            else False
        )

    def __eq__(self, other):
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def _missing_(cls, value):
        """Handle creation from value, name, or title."""
        if isinstance(value, int):
            for enum in cls:
                if enum.value == value:
                    return enum
        if isinstance(value, str):
            for enum in cls:
                if enum.__doc__ and enum.__doc__.lower() == value.lower():
                    return enum
            if value in cls.__members__:
                return cls.__members__[value]
        raise ValueError(f"{value} is not a valid {cls.__name__}")


class ApprovalStatus(BaseTitledEnum):
    NOAPPROVAL = None, 0
    REJECTED = "Disapproved", 1
    APPROVED = "Approved", 2

    @classmethod
    def get_mapping(cls) -> typing.Dict[str, int]:
        return {i.__repr__(): i.value for i in list(cls)}


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
    TILED = "Tiled", 5
    OTHER = "Other", 6
    POINT_CLOUD = "PointCloud", 7
    MULTIMODAL = "Multimodal", 8
    UNSUPPORTED_TYPE_1 = "UnsupportedType", 9
    UNSUPPORTED_TYPE_2 = "UnsupportedType", 10

    @classproperty
    def images(self):
        return self.VECTOR.value, self.PIXEL.value, self.TILED.value


class StepsType(Enum):
    INITIAL = 1
    BASIC = 2
    KEYPOINT = 3


class UserRole(BaseTitledEnum):
    CONTRIBUTOR = "Contributor", 4
    ADMIN = "Admin", 7


class UploadState(Enum):
    INITIAL = 1
    BASIC = 2
    EXTERNAL = 3


class ImageQuality(BaseTitledEnum):
    ORIGINAl = "original", 100
    COMPRESSED = "compressed", 60


class ProjectStatus(BaseTitledEnum):
    Undefined = "Undefined", -1
    NotStarted = "NotStarted", 1
    InProgress = "InProgress", 2
    Completed = "Completed", 3
    OnHold = "OnHold", 4


class FolderStatus(BaseTitledEnum):
    Undefined = "Undefined", -1
    NotStarted = "NotStarted", 1
    InProgress = "InProgress", 2
    Completed = "Completed", 3
    OnHold = "OnHold", 4


class ExportStatus(BaseTitledEnum):
    IN_PROGRESS = "inProgress", 1
    COMPLETE = "complete", 2
    CANCELED = "canceled", 3
    ERROR = "error", 4


class ClassTypeEnum(BaseTitledEnum):
    OBJECT = "object", 1
    TAG = "tag", 2
    RELATIONSHIP = "relationship", 3

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
    CUSTOM = "custom", 4
    DATABRICKS = "databricks", 5
    SNOWFLAKE = "snowflake", 6


class TrainingStatus(BaseTitledEnum):
    NOT_STARTED = "NotStarted", 1
    IN_PROGRESS = "InProgress", 2
    COMPLETED = "Completed", 3
    FAILED_BEFORE_EVALUATION = "FailedBeforeEvaluation", 4
    FAILED_AFTER_EVALUATION = "FailedAfterEvaluation", 5
    FAILED_AFTER_EVALUATION_WITH_SAVE_MODEL = "FailedAfterEvaluationWithSavedModel", 6


class CustomFieldEntityEnum(str, Enum):
    CONTRIBUTOR = "Contributor"
    TEAM = "Team"
    PROJECT = "Project"


class CustomFieldType(Enum):
    Text = 1
    MULTI_SELECT = 2
    SINGLE_SELECT = 3
    DATE_PICKER = 4
    NUMERIC = 5


class WMUserStateEnum(str, Enum):
    Pending = "PENDING"
    Confirmed = "CONFIRMED"
