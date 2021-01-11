from .db.project_metadata import get_project_metadata
from .exceptions import SABaseException
from .ml.ml_models import search_models
from inspect import signature
from .common import project_type_int_to_str
from functools import wraps


def project_metadata(func):

    sig = signature(func)

    @wraps(func)
    def inner(*args, **kwargs):
        new_kwargs = sig.bind(*args, **kwargs)
        new_kwargs = new_kwargs.arguments

        if isinstance(new_kwargs['project'], str):
            new_kwargs['project'] = get_project_metadata(
                new_kwargs['project'], include_complete_image_count=True
            )

        elif isinstance(new_kwargs['project'], list):

            types = (type(x) for x in new_kwargs['project'])
            types = set(types)

            if len(types) != 1:
                raise SABaseException(
                    0,
                    "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
                )

            current_chosen_type = types.pop()
            if current_chosen_type is str:
                for idx, item in enumerate(new_kwargs['project']):
                    new_kwargs['project'][idx] = get_project_metadata(
                        item, include_complete_image_count=True
                    )
            elif current_chosen_type is not dict:
                raise SABaseException(
                    0,
                    "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
                )
        elif not isinstance(new_kwargs['project'], dict):
            raise SABaseException(
                0,
                "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
            )

        return func(**new_kwargs)

    return inner


def model_metadata(func):

    sig = signature(func)

    @wraps(func)
    def inner(*args, **kwargs):
        new_kwargs = sig.bind(*args, **kwargs)
        new_kwargs = new_kwargs.arguments

        if 'model' in new_kwargs:
            model_keyword = 'model'
        else:
            model_keyword = 'base_model'

        if isinstance(new_kwargs[model_keyword], str):

            all_models = search_models(
                include_global=True, name=new_kwargs[model_keyword]
            )
            if len(all_models) > 1:
                raise SABaseException(
                    0,
                    "There are several models with the same name, this functionality is not supported with the SDK"
                )
            all_models_name_map = {x['name']: x for x in all_models}
            if new_kwargs[model_keyword] not in all_models_name_map:
                raise SABaseException(
                    0,
                    f"The specifed model does not exist. Available models are {list(all_models_name_map.keys())}"
                )
            new_kwargs[model_keyword] = all_models_name_map[
                new_kwargs[model_keyword]]
            new_kwargs[model_keyword]['type'] = project_type_int_to_str(
                new_kwargs[model_keyword]['type']
            )

        elif not isinstance(new_kwargs[model_keyword], dict):
            raise SABaseException(
                0, "The model parameter should either be string or a dict"
            )

        return func(**new_kwargs)

    return inner
