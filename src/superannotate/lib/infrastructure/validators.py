import os
from collections import defaultdict

from lib.core.entities import DocumentAnnotation
from lib.core.entities import PixelAnnotation
from lib.core.entities import VectorAnnotation
from lib.core.entities import VideoExportAnnotation
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
        if "__root__" in errors_list:
            errors_list.remove("__root__")
        errors_list[1::] = [
            f"[{i}]" if isinstance(i, int) else f".{i}" for i in errors_list[1::]
        ]
        error_messages["".join([str(item) for item in errors_list])].append(
            error["msg"]
        )
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

    def is_valid(self) -> bool:
        try:
            self._validate()
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
    MODEL = VideoExportAnnotation


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
