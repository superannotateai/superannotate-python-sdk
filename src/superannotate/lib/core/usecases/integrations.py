from typing import Dict
from typing import Optional

from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import FolderEntity
from lib.core.entities import IntegrationEntity
from lib.core.entities import ProjectEntity
from lib.core.entities.integrations import IntegrationTypeEnum
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases import BaseReportableUseCase


class GetIntegrations(BaseReportableUseCase):
    def __init__(self, reporter: Reporter, service_provider: BaseServiceProvider):

        super().__init__(reporter)
        self._service_provider = service_provider

    def execute(self) -> Response:
        integrations = self._service_provider.integrations.list().data.integrations
        integrations = list(sorted(integrations, key=lambda x: x.createdAt))
        integrations.reverse()
        self._response.data = integrations
        return self._response


class AttachIntegrations(BaseReportableUseCase):
    MULTIMODAL_INTEGRATIONS = [
        IntegrationTypeEnum.DATABRICKS,
        IntegrationTypeEnum.SNOWFLAKE,
    ]

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        service_provider: BaseServiceProvider,
        integration: IntegrationEntity,
        folder_path: str = None,
        query: Optional[str] = None,
        item_name_column: Optional[str] = None,
        custom_item_name: Optional[str] = None,
        component_mapping: Optional[Dict[str, str]] = None,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._integration = integration
        self._service_provider = service_provider
        self._folder_path = folder_path
        self._query = query
        self._item_name_column = item_name_column
        self._custom_item_name = custom_item_name
        self._component_mapping = component_mapping
        self._options = {}  # using only for Databricks and Snowflake
        self._item_category_column = None

    @property
    def _upload_path(self):
        return f"{self._project.name}{f'/{self._folder.name}' if self._folder.name != 'root' else ''}"

    def validate_integration(self):
        # TODO add support in next iterations
        if self._integration.type == IntegrationTypeEnum.SNOWFLAKE:
            raise AppException(
                "Attaching items is not supported with Snowflake integration."
            )

        if self._integration.type in self.MULTIMODAL_INTEGRATIONS:
            if self._project.type != ProjectType.MULTIMODAL:
                raise AppException(
                    f"{self._integration.name} integration is supported only for Multimodal projects."
                )

    def validate_options_for_multimodal_integration(self):
        if self._integration.type in self.MULTIMODAL_INTEGRATIONS:
            if self._item_name_column and self._custom_item_name:
                raise AppException(
                    "‘item_name_column and custom_item_name cannot be used simultaneously."
                )

            if not self._item_name_column and not self._custom_item_name:
                raise AppException(
                    "Either item_name_column or custom_item_name is required."
                )

            if not all((self._query, self._component_mapping)):
                raise AppException(
                    f"{self._integration.name} integration requires both a query and component_mapping."
                )

            category_setting: bool = bool(
                next(
                    (
                        setting.value
                        for setting in self._service_provider.projects.list_settings(
                            self._project
                        ).data
                        if setting.attribute == "CategorizeItems"
                    ),
                    None,
                )
            )
            if (
                not category_setting
                and "_item_category" in self._component_mapping.values()
            ):
                raise AppException(
                    "Item Category must be enabled for a project to use _item_category"
                )

            self._item_category_column = next(
                (
                    k
                    for k, v in self._component_mapping.items()
                    if v == "_item_category"
                ),
                None,
            )
            if self._item_category_column:
                del self._component_mapping[self._item_category_column]

            sa_components = [
                c.name.lower()
                for c in self._service_provider.annotation_classes.list(
                    condition=Condition("project_id", self._project.id, EQ)
                ).data
            ]

            for i in self._component_mapping.values():
                if i.lower() not in sa_components:
                    raise AppException(
                        f"Component mapping contains invalid component ID: `{i}`"
                    )

    def generate_options_for_multimodal_integration(self):
        self._options["query"] = self._query
        self._options["item_name"] = (
            self._custom_item_name if self._custom_item_name else self._item_name_column
        )
        self._options["prefix"] = True if self._custom_item_name else False
        self._options["column_class_map"] = self._component_mapping
        if self._item_category_column:
            self._options["item_category"] = self._item_category_column

    def execute(self) -> Response:
        if self.is_valid():
            if self._integration.type in self.MULTIMODAL_INTEGRATIONS:
                self.generate_options_for_multimodal_integration()

            self.reporter.log_info(
                "Attaching file(s) from "
                f"{self._integration.root}{f'/{self._folder_path}' if self._folder_path else ''} "
                f"to {self._upload_path}. This may take some time."
            )

            attache_response = self._service_provider.integrations.attach_items(
                project=self._project,
                folder=self._folder,
                integration=self._integration,
                folder_name=self._folder_path
                if self._integration.type not in self.MULTIMODAL_INTEGRATIONS
                else None,
                options=self._options if self._options else None,
            )
            if not attache_response.ok:
                self._response.errors = AppException(
                    f"An error occurred for {self._integration.name}. Please make sure: "
                    "\n - The bucket exists."
                    "\n - The connection is valid."
                    "\n - The path to a specified directory is correct."
                )
            return self._response
