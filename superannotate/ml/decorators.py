from ..db.project import get_project_metadata
from ..exceptions import SABaseException
from .ml_models import search_models

def project_metadata(func):
    def inner(**kwargs):

        if isinstance(kwargs["project"], str):
            kwargs["project"] = get_project_metadata(kwargs["project"])

        elif isinstance(kwargs["project"], list):
            types = (type(x) for x in kwargs["project"])

            if len(types) != 1:
                raise SABaseException(
                    0, "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
                )

            current_chosen_type = types.pop()

            if current_chosen_type is str:
                for item in kwargs["project"]:
                    item = get_project_metadata(item)
            elif current_chosen_type is not dict:
                raise SABaseException(
                    0, "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
                )
        elif not isinstance(kwargs["project"], dict):
            raise SABaseException(
                0, "The 'project' argument should be a dict, a string, a list of strings or a list of dicts"
            )

        func(**kwargs)
    return inner

def model_metadata(func):
    def inner(**kwargs):
        if isinstance(kwargs["model"], str):
            type_ = None

            if 'project' in kwargs:
                type_ =  kwargs['project']['type']

            all_models = search_models(type_ = type_, include_global = True)
            all_models_name_map = {x['name'] : x for x in all_models}
            if kwargs["model"] not in all_models_name_map:
                raise SABaseException(
                    0, f"The specifed model does not exist. Available models are {list(all_models_name_map.keys())}"
                )
            kwargs["model"] = all_models_name_map[kwargs["model"]]
        elif not isninstance(kwargs["model"], dict):
            raise SABaseException(
                0, "The model parameter should either be string or a dict"
            )
        func(**kwargs)
    return inner
