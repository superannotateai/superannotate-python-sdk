import concurrent.futures
import logging
import platform
import tempfile
import time
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

import boto3
import lib.core as constances
import pandas as pd
import requests
from lib.app.analytics.aggregators import DataAggregator
from lib.app.analytics.common import consensus
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import ProjectEntity
from lib.core.enums import ExportStatus
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.reporter import Reporter
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases.annotations import DownloadAnnotations
from lib.core.usecases.base import BaseReportableUseCase
from lib.core.usecases.base import BaseUseCase
from lib.core.usecases.classes import DownloadAnnotationClassesUseCase
from lib.core.usecases.folders import GetFolderUseCase

logger = logging.getLogger("sa")


class PrepareExportUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder_names: List[str],
        service_provider: BaseServiceProvider,
        include_fuse: bool,
        only_pinned: bool,
        annotation_statuses: List[str] = None,
        integration_id: int = None,
        export_type: int = None,
    ):
        super().__init__()
        self._project = project
        self._folder_names = list(folder_names) if folder_names else None
        self._service_provider = service_provider
        self._annotation_statuses = annotation_statuses
        self._include_fuse = include_fuse
        self._only_pinned = only_pinned
        self._integration_id = integration_id
        self._export_type = export_type

    def validate_only_pinned(self):
        if (
            self._project.upload_state == constances.UploadState.EXTERNAL.value
            and self._only_pinned
        ):
            raise AppValidationException(
                f"Pin functionality is not supported for  projects containing {self._project.type} attached with URLs"
            )

    def validate_fuse(self):
        if (
            self._project.upload_state == constances.UploadState.EXTERNAL.value
            and self._include_fuse
        ):
            raise AppValidationException(
                "Include fuse functionality is not supported for  projects containing "
                f"{ProjectType(self._project.type).name} attached with URLs"
            )

    def validate_export_type(self):
        if self._export_type == 2:
            if (
                self._project.type != ProjectType.VECTOR.value
                or self._project.upload_state != constances.UploadState.EXTERNAL.value
            ):
                raise AppValidationException(
                    "COCO format is not supported for this project."
                )
        elif self._export_type == 3 and self._project.type != ProjectType.GEN_AI.value:
            raise AppValidationException(
                "CSV format is not supported for this project."
            )

    def validate_folder_names(self):
        if self._folder_names:
            condition = Condition("project_id", self._project.id, EQ)
            existing_folders = {
                folder.name
                for folder in self._service_provider.folders.list(condition).data
            }
            folder_names_set = set(self._folder_names)
            if not folder_names_set.issubset(existing_folders):
                raise AppException(
                    f"Folder(s) {', '.join(folder_names_set - existing_folders)} does not exist"
                )

    def execute(self):
        if self.is_valid():
            if self._project.upload_state == constances.UploadState.EXTERNAL.value:
                self._include_fuse = False
            kwargs = dict(
                project=self._project,
                folders=self._folder_names,
                include_fuse=self._include_fuse,
                only_pinned=self._only_pinned,
                integration_id=self._integration_id,
            )
            if self._annotation_statuses:
                kwargs["annotation_statuses"] = self._annotation_statuses
            if self._export_type:
                kwargs["export_type"] = self._export_type
            response = self._service_provider.prepare_export(**kwargs)
            if not response.ok:
                raise AppException(response.error)

            report_message = ""
            if self._folder_names:
                report_message = f"[{', '.join(self._folder_names)}] "
            logger.info(
                f"Prepared export {response.data['name']} for project {self._project.name} "
                f"{report_message}(project ID {self._project.id})."
            )
            self._response.data = response.data
        return self._response


class GetExportsUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
        return_metadata: bool = False,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._project = project
        self._return_metadata = return_metadata

    def execute(self):
        if self.is_valid():
            data = self._service_provider.get_exports(self._project).data
            self._response.data = data
            if not self._return_metadata:
                self._response.data = [i["name"] for i in data]
        return self._response


class DownloadExportUseCase(BaseReportableUseCase):
    FORBIDDEN_CHARS = "*/\\[]:;|,\"'"

    def __init__(
        self,
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
        export_name: str,
        folder_path: str,
        extract_zip_contents: bool,
        to_s3_bucket: bool,
        reporter: Reporter,
    ):
        super().__init__(reporter)
        self._service_provider = service_provider
        self._project = project
        self._export_name = export_name
        self._folder_path = folder_path if folder_path else ""
        self._extract_zip_contents = extract_zip_contents
        self._to_s3_bucket = to_s3_bucket

    def upload_to_s3_from_folder(self, source: str, folder_path: str):
        to_s3_bucket = boto3.Session().resource("s3").Bucket(self._to_s3_bucket)
        files_to_upload = list(Path(source).rglob("*.*"))

        def _upload_file_to_s3(_to_s3_bucket, _path, _s3_key) -> None:
            _to_s3_bucket.upload_file(str(_path), _s3_key)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = []
            self.reporter.start_spinner()
            for path in files_to_upload:
                s3_key = f"{folder_path + '/' if folder_path else ''}{str(Path(path).relative_to(Path(source)))}"
                results.append(
                    executor.submit(_upload_file_to_s3, to_s3_bucket, path, s3_key)
                )
            self.reporter.stop_spinner()

    def download_to_local_storage(self, destination: str, extract_zip=False):
        exports = self._service_provider.get_exports(project=self._project).data
        export = next(filter(lambda i: i["name"] == self._export_name, exports), None)
        export = self._service_provider.get_export(
            project=self._project, export_id=export["id"]
        ).data
        if not export:
            raise AppException("Export not found.")
        export_status = export["status"]
        if export_status != ExportStatus.COMPLETE.value:
            logger.info("Waiting for export to finish on server.")
            self.reporter.start_spinner()
            while export_status != ExportStatus.COMPLETE.value:
                response = self._service_provider.get_export(
                    project=self._project,
                    export_id=export["id"],
                )
                if not response.ok:
                    raise AppException(response.error)
                export = response.data
                export_status = export["status"]
                if export_status in (
                    ExportStatus.ERROR.value,
                    ExportStatus.CANCELED.value,
                ):
                    self.reporter.stop_spinner()
                    raise AppException("Couldn't download export.")
                time.sleep(1)
            self.reporter.stop_spinner()
        filename = export["name"]
        if platform.system().lower() == "windows":
            for char in DownloadExportUseCase.FORBIDDEN_CHARS:
                filename = filename.replace(char, "_")
        filepath = Path(destination) / filename
        with requests.get(export["download"], stream=True) as response:
            response.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        if extract_zip:
            with zipfile.ZipFile(filepath, "r") as f:
                f.extractall(destination)
            Path.unlink(filepath)
        return export["id"], filepath, destination

    def execute(self):
        if self.is_valid():
            if self._to_s3_bucket:
                with tempfile.TemporaryDirectory() as temp_dir:
                    self.download_to_local_storage(
                        temp_dir, extract_zip=self._extract_zip_contents
                    )
                    self.upload_to_s3_from_folder(temp_dir, self._folder_path)
                self.reporter.log_info(
                    f"Exported to AWS {self._to_s3_bucket}/{self._folder_path}"
                )
            else:
                export_id, filepath, destination = self.download_to_local_storage(
                    self._folder_path, self._extract_zip_contents
                )
                if self._extract_zip_contents:
                    self.reporter.log_info(
                        f"Extracted {filepath} to folder {destination}"
                    )
                else:
                    self.reporter.log_info(
                        f"Downloaded export ID {export_id} to {filepath}"
                    )
        return self._response


class ConsensusUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder_names: list,
        image_list: list,
        annotation_type: str,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._project = project
        self._image_list = image_list
        self._instance_type = annotation_type
        self._folders = []
        self._folder_names = folder_names
        self.service_provider = service_provider

        for folder_name in folder_names:
            get_folder_uc = GetFolderUseCase(
                project=self._project,
                service_provider=service_provider,
                folder_name=folder_name,
            )
            folder = get_folder_uc.execute().data
            if not folder:
                raise AppException(f"Can't find folder {folder_name}")

            self._folders.append(folder)

    def _download_annotations(self, destination):
        reporter = Reporter(
            log_info=False,
            log_warning=False,
            log_debug=False,
            disable_progress_bar=True,
        )

        classes_dir = Path(destination) / "classes"
        classes_dir.mkdir()

        DownloadAnnotationClassesUseCase(
            reporter=reporter,
            download_path=classes_dir,
            project=self._project,
            service_provider=self.service_provider,
        ).execute()

        for folder in self._folders:
            download_annotations_uc = DownloadAnnotations(
                reporter=reporter,
                project=self._project,
                folder=folder,
                item_names=self._image_list,
                destination=destination,  # Destination unknown known known
                service_provider=self.service_provider,
                recursive=False,
            )
            tmp = download_annotations_uc.execute()
            if tmp.errors:
                raise AppException(tmp.errors)
        return tmp.data

    def execute(self):
        with TemporaryDirectory() as temp_dir:
            export_path = self._download_annotations(temp_dir)
            aggregator = DataAggregator(
                project_type=self._project.type,
                folder_names=self._folder_names,
                project_root=export_path,
            )
            project_df = aggregator.aggregate_annotations_as_df()

        all_projects_df = project_df[project_df["instanceId"].notna()]
        all_projects_df = all_projects_df.loc[
            all_projects_df["folderName"].isin(self._folder_names)
        ]

        if self._image_list is not None:
            all_projects_df = all_projects_df.loc[
                all_projects_df["itemName"].isin(self._image_list)
            ]

        all_projects_df.query("type == '" + self._instance_type + "'", inplace=True)

        def aggregate_attributes(instance_df):
            def attribute_to_list(attribute_df):
                attribute_names = list(attribute_df["attributeName"])
                attribute_df["attributeNames"] = len(attribute_df) * [attribute_names]
                return attribute_df

            attributes = None
            if not instance_df["attributeGroupName"].isna().all():
                attrib_group_name = instance_df.groupby("attributeGroupName")[
                    ["attributeGroupName", "attributeName"]
                ].apply(attribute_to_list)
                attributes = dict(
                    zip(
                        attrib_group_name["attributeGroupName"],
                        attrib_group_name["attributeNames"],
                    )
                )

            instance_df.drop(
                ["attributeGroupName", "attributeName"], axis=1, inplace=True
            )
            instance_df.drop_duplicates(
                subset=["itemName", "instanceId", "folderName"], inplace=True
            )
            instance_df["attributes"] = [attributes]
            return instance_df

        if self._instance_type != "tag":
            all_projects_df = all_projects_df.groupby(
                ["itemName", "instanceId", "folderName"]
            )
            all_projects_df = all_projects_df.apply(aggregate_attributes).reset_index(
                drop=True
            )
            unique_images = set(all_projects_df["itemName"])
        else:
            unique_images = all_projects_df["itemName"].unique()
        all_consensus_data = []
        for image_name in unique_images:
            image_data = consensus(all_projects_df, image_name, self._instance_type)
            all_consensus_data.append(pd.DataFrame(image_data))

        consensus_df = pd.concat(all_consensus_data, ignore_index=True)
        if self._instance_type == "tag":
            consensus_df["score"] /= len(self._folder_names) - 1

        self._response.data = consensus_df
        return self._response
