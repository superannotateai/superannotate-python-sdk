import os
from collections import defaultdict

from lib.core.types import DocumentAnnotation
from lib.core.types import PixelAnnotation
from lib.core.types import VectorAnnotation
from lib.core.types import VideoAnnotation
from lib.core.validators import BaseAnnotationValidator
from lib.core.validators import BaseValidator
from pydantic import ValidationError


def get_tabulation() -> int:
    try:
        return int(os.get_terminal_size().columns / 2)
    except OSError:
        return 48


def wrap_error(e: ValidationError) -> str:
    tabulation = get_tabulation()
    error_messages = defaultdict(list)
    for error in e.errors():
        errors_list = list(error["loc"])
        errors_list[1::2] = [f"[{i}]" for i in errors_list[1::2]]
        errors_list[2::2] = [f".{i}" for i in errors_list[2::2]]
        error_messages["".join(errors_list)].append(error["msg"])
    texts = ["\n"]
    for field, text in error_messages.items():
        texts.append(
            "{} {}{}".format(
                field,
                " " * (tabulation - len(field)),
                f"\n {' ' * tabulation}".join(text),
            )
        )
    return "\n".join(texts)


class BaseSchemaValidator(BaseValidator):
    MODEL = PixelAnnotation

    @classmethod
    def validate(cls, data: dict):
        cls.MODEL(**data)

    def is_valid(self) -> bool:
        try:
            self.validate(self._data)
        except ValidationError as e:
            self._validation_output = e
        return not bool(self._validation_output)

    def generate_report(self) -> str:
        return wrap_error(self._validation_output)


class PixelValidator(BaseSchemaValidator):
    MODEL = PixelAnnotation


class VectorValidator(BaseSchemaValidator):
    MODEL = VectorAnnotation


class VideoValidator(BaseSchemaValidator):
    MODEL = VideoAnnotation


class DocumentValidator(BaseSchemaValidator):
    MODEL = DocumentAnnotation


class AnnotationValidator(BaseAnnotationValidator):
    @classmethod
    def get_pixel_validator(cls):
        return PixelValidator

    @classmethod
    def get_vector_validator(cls):
        return VectorValidator

    @classmethod
    def get_video_validator(cls):
        return VideoValidator

    @classmethod
    def get_document_validator(cls):
        return DocumentValidator
