from lib.core import entities
from lib.core.conditions import Condition
from lib.core.serviceproviders import BaseModelsService


class ModelsService(BaseModelsService):
    URL_MODEL = "ml_model"
    URL_MODELS = "ml_models"

    def delete(self, model_id: int):
        return self.client.request(f"{self.URL_MODEL}/{model_id}", "delete")

    def start_training(self, hyper_parameters: dict):
        return self.client.request(
            self.URL_MODELS,
            "post",
            data=hyper_parameters,
        )

    def list(self, condition: Condition = None):
        search_model_url = self.URL_MODELS
        if condition:
            search_model_url = f"{search_model_url}?{condition.build_query()}"
        return self.client.paginate(search_model_url, item_type=entities.MLModelEntity)
