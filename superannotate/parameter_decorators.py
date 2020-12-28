from .db.project_metadata import get_project_metadata
from .exceptions import SABaseException
from .ml.ml_models import search_models
from inspect import getcallargs
from .common import project_type_int_to_str
from functools import wraps

def transform_arg(argname, pred):
    def transformer(func):
        original_func = getattr(func, "original_func", func)

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            kwargs = getcallargs(original_func, *args, **kwargs)
            kwargs[argname] = pred(kwargs[argname])
            return func(**kwargs)

        wrapped_func.original_func = original_func

        return wrapped_func
    return transformer

def process_project_arg(project):

    if isinstance(project, str):
        project = get_project_metadata(project, include_complete_image_count = True)
        #project['type'] = project_type_int_to_str(project['type'])
    elif isinstance(project, list):
        types = (type(x) for x in project)
        types = set(types)
        if len(types) != 1:
            raise SABaseException(
                0, "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
            )

        current_chosen_type = types.pop()
        if current_chosen_type is str:
            for idx, item in enumerate(project):
                project[idx] = get_project_metadata(item, include_complete_image_count = True)
        elif current_chosen_type is not dict:
            raise SABaseException(
                0, "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
            )
    elif not isinstance(project, dict):
        raise SABaseException(
            0, "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
        )
    return project

def process_model_arg(model):

    if isinstance(model, str):
        all_models = search_models(include_global = True)
        all_models_name_map = {x['name'] : x for x in all_models  }
        if model not in all_models_name_map:
            raise SABaseException(
                0, f"The specifed model does not exist. Available models are {list(all_models_name_map.keys())}"
            )
        model = all_models_name_map[model]
        model['type'] = project_type_int_to_str(model['type'])
    elif not isinstance(model, dict):
        raise SABaseException(
            0, "The model parameter should either be string or a dict"

        )

    return model


project_metadata = transform_arg("project", process_project_arg)
model_metadata = transform_arg("model", process_model_arg)
