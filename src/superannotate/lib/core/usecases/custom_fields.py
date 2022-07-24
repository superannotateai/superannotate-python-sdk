from typing import Dict
from typing import List

from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases import BaseReportableUseCase


class CreateCustomSchemaUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        schema: dict,
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._schema = schema
        self._backend_client = backend_client

    def execute(self) -> Response:
        response = self._backend_client.create_custom_schema(
            team_id=self._project.team_id,
            project_id=self._project.id,
            schema=self._schema,
        )
        if response.ok:
            self._response.data = response.data
        else:
            errors = response.data.get("errors")
            if errors:
                separator = "\n- "
                report = separator + separator.join(errors)
            else:
                report = response.error
            self._response.errors = report
        return self._response


class GetCustomSchemaUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._backend_client = backend_client

    def execute(self) -> Response:
        response = self._backend_client.get_custom_schema(
            team_id=self._project.team_id,
            project_id=self._project.id,
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
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._fields = fields
        self._backend_client = backend_client

    def execute(self) -> Response:
        if self._fields:
            self.reporter.log_info("Matched fields deleted from schema.")
        response = self._backend_client.delete_custom_schema(
            team_id=self._project.team_id,
            project_id=self._project.id,
            fields=self._fields,
        )
        if response.ok:
            use_case_response = GetCustomSchemaUseCase(
                reporter=self.reporter,
                project=self._project,
                backend_client=self._backend_client,
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
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._items = items
        self._backend_client = backend_client

    def execute(self) -> Response:
        uploaded_items, failed_items = [], []
        self.reporter.log_info(
            "Validating metadata against the schema of the custom fields. "
            "Valid metadata will be attached to the specified item."
        )
        with self.reporter.spinner:
            for idx in range(0, len(self._items), self.CHUNK_SIZE):
                response = self._backend_client.upload_custom_fields(
                    project_id=self._project.id,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
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
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._items = items
        self._backend_client = backend_client

    def execute(self) -> Response:
        for idx in range(0, len(self._items), self.CHUNK_SIZE):
            response = self._backend_client.delete_custom_fields(
                project_id=self._project.id,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                items=self._items[idx : idx + self.CHUNK_SIZE],  # noqa: E203
            )
            if not response.ok:
                self._response.errors = response.error
                return self._response
        self.reporter.log_info(
            "Corresponding fields and their values removed from items."
        )
        return self._response
