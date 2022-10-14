from typing import Dict
from typing import List

from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases import BaseReportableUseCase


class CreateCustomSchemaUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        schema: dict,
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._schema = schema
        self._service_provider = service_provider

    def execute(self) -> Response:
        response = self._service_provider.custom_fields.create_schema(
            project=self._project,
            schema=self._schema,
        )
        if response.ok:
            self._response.data = response.data
        else:
            error = response.error
            if isinstance(error, list):
                error = "-" + "\n-".join(error)
            self._response.errors = error
        return self._response


class GetCustomSchemaUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._service_provider = service_provider

    def execute(self) -> Response:
        response = self._service_provider.custom_fields.get_schema(
            project=self._project
        )
        if response.ok:
            self._response.data = response.data
        else:
            self._response.errors = response.error
        return self._response


class DeleteCustomSchemaUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        fields: List[str],
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._fields = fields
        self._service_provider = service_provider

    def execute(self) -> Response:
        if self._fields:
            self.reporter.log_info("Matched fields deleted from schema.")
        response = self._service_provider.custom_fields.delete_fields(
            project=self._project,
            fields=self._fields,
        )
        if response.ok:
            use_case_response = GetCustomSchemaUseCase(
                reporter=self.reporter,
                project=self._project,
                service_provider=self._service_provider,
            ).execute()
            if use_case_response.errors:
                self._response.errors = use_case_response.errors
            else:
                self._response.data = use_case_response.data
        else:
            self._response.errors = response.error
        return self._response


class UploadCustomValuesUseCase(BaseReportableUseCase):
    CHUNK_SIZE = 5000

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        items: List[Dict[str, str]],
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._items = items
        self._service_provider = service_provider

    def execute(self) -> Response:
        uploaded_items, failed_items = [], []
        self.reporter.log_info(
            "Validating metadata against the schema of the custom fields. "
            "Valid metadata will be attached to the specified item."
        )
        with self.reporter.spinner:
            for idx in range(0, len(self._items), self.CHUNK_SIZE):
                response = self._service_provider.custom_fields.upload_fields(
                    project=self._project,
                    folder=self._folder,
                    items=self._items[idx : idx + self.CHUNK_SIZE],  # noqa: E203
                )
                if not response.ok:
                    self._response.errors = response.error
                    return self._response
                failed_items.extend(response.data.failed_items)

        if failed_items:
            self.reporter.log_error(
                f"The metadata dicts of {len(failed_items)} items are invalid because they don't match "
                f'the schema of the custom fields defined for the "{self._project.name}" project.'
            )
        self._response.data = {
            "succeeded": list(
                {list(item)[0] for item in self._items} ^ set(failed_items)
            ),
            "failed": failed_items,
        }
        return self._response


class DeleteCustomValuesUseCase(BaseReportableUseCase):
    CHUNK_SIZE = 5000

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        items: List[Dict[str, List[str]]],
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._items = items
        self._service_provider = service_provider

    def execute(self) -> Response:
        for idx in range(0, len(self._items), self.CHUNK_SIZE):
            response = self._service_provider.custom_fields.delete_values(
                project=self._project,
                folder=self._folder,
                items=self._items[idx : idx + self.CHUNK_SIZE],  # noqa: E203
            )
            if not response.ok:
                self._response.errors = response.error
                return self._response
        self.reporter.log_info(
            "Corresponding fields and their values removed from items."
        )
        return self._response
