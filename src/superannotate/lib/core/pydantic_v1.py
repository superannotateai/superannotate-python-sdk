from packaging.version import parse as parse_version
from pydantic import VERSION

if parse_version(VERSION).major < 2:
    import pydantic
else:
    import pydantic.v1 as pydantic  # noqa

BaseModel = pydantic.BaseModel
Field = pydantic.Field
Extra = pydantic.Extra
ValidationError = pydantic.ValidationError
StrictStr = pydantic.StrictStr
StrictInt = pydantic.StrictInt
StrictBool = pydantic.StrictBool
StrictFloat = pydantic.StrictFloat
ErrorWrapper = pydantic.error_wrappers.ErrorWrapper
parse_obj_as = pydantic.parse_obj_as
is_namedtuple = pydantic.typing.is_namedtuple  # noqa
Literal = pydantic.typing.Literal  # noqa
ValueItems = pydantic.utils.ValueItems  # noqa
ROOT_KEY = pydantic.utils.ROOT_KEY  # noqa
sequence_like = pydantic.utils.sequence_like  # noqa
validator = pydantic.validator  # noqa
constr = pydantic.constr  # noqa
conlist = pydantic.conlist  # noqa
parse_datetime = pydantic.datetime_parse.parse_datetime  # noqa
Color = pydantic.color.Color  # noqa
ColorType = pydantic.color.ColorType  # noqa
validators = pydantic.validators  # noqa
WrongConstantError = pydantic.errors.WrongConstantError
errors = pydantic.errors
PydanticTypeError = pydantic.errors.PydanticTypeError
pydantic_validate_arguments = pydantic.validate_arguments
StrRegexError = pydantic.errors.StrRegexError
create_model_from_typeddict = pydantic.annotated_types.create_model_from_typeddict
