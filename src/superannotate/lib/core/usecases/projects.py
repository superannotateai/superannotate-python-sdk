import copy
import decimal
from collections import defaultdict
from typing import List

import lib.core as constances
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AnnotationClassEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import SettingEntity
from lib.core.entities import TeamEntity
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases.base import BaseReportableUseCase
from lib.core.usecases.base import BaseUseCase
from lib.core.usecases.base import BaseUserBasedUseCase
from requests.exceptions import RequestException
from superannotate.logger import get_default_logger

logger = get_default_logger()


class GetProjectsUseCase(BaseUseCase):
    def __init__(
        self,
        condition: Condition,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._condition = condition
        self._service_provider = service_provider

    def execute(self):
        if self.is_valid():
            response = self._service_provider.projects.list(self._condition)
            if response.ok:
                self._response.data = response.data
            else:
                self._response.errors = response.errors
        return self._response


class GetProjectByNameUseCase(BaseUseCase):
    def __init__(
        self,
        name: str,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._name = name
        self._service_provider = service_provider

    def execute(self):
        if self.is_valid():
            condition = Condition("name", self._name, EQ)
            response = self._service_provider.projects.list(condition)
            if response.ok:
                if not response.data:
                    self._response.errors = AppException("Project not found.")
                else:
                    project = next(
                        (
                            project
                            for project in response.data
                            if project.name == self._name
                        ),
                        None,
                    )
                    if not project:
                        self._response.errors = AppException("Project not found")
                    self._response.data = project

        return self._response


class GetProjectMetaDataUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
        include_annotation_classes: bool,
        include_settings: bool,
        include_workflow: bool,
        include_contributors: bool,
        include_complete_image_count: bool,
    ):
        super().__init__(reporter)
        self._project = project
        self._service_provider = service_provider

        self._include_annotation_classes = include_annotation_classes
        self._include_settings = include_settings
        self._include_workflow = include_workflow
        self._include_contributors = include_contributors
        self._include_complete_image_count = include_complete_image_count

    def execute(self):
        project = self._service_provider.projects.get(self._project.id).data
        if self._include_complete_image_count:
            folders = self._service_provider.folders.list(
                Condition("project_id", self._project.id, EQ)
                & Condition("completedImagesCount", True, EQ)
            ).data
            root_completed_count = 0
            total_completed_count = 0
            for folder in folders:
                try:
                    total_completed_count += folder.completedCount  # noqa
                    if folder.is_root:
                        root_completed_count = folder.completedCount  # noqa
                except AttributeError:
                    pass
            project.root_folder_completed_images_count = root_completed_count
            project.completed_images_count = total_completed_count
        if self._include_annotation_classes:
            project.classes = self._service_provider.annotation_classes.list(
                Condition("project_id", self._project.id, EQ)
            ).data

        if self._include_settings:
            project.settings = self._service_provider.projects.list_settings(
                self._project
            ).data

        if self._include_workflow:
            project.workflows = (
                GetWorkflowsUseCase(
                    project=self._project, service_provider=self._service_provider
                )
                .execute()
                .data
            )

        if self._include_contributors:
            project.contributors = project.users
        else:
            project.users = []
        self._response.data = project
        return self._response


class CreateProjectUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
    ):

        super().__init__()
        self._project = project
        self._service_provider = service_provider

    def validate_settings(self):
        for setting in self._project.settings[:]:
            if setting.attribute == "WorkflowType":
                self._project.settings.remove(setting)
            if setting.attribute == "ImageQuality" and isinstance(setting.value, str):
                setting.value = constances.ImageQuality.get_value(setting.value)
            elif setting.attribute == "FrameRate":
                if not self._project.type == constances.ProjectType.VIDEO.value:
                    raise AppValidationException(
                        "FrameRate is available only for Video projects"
                    )
                if isinstance(setting.value, (float, int)):
                    if (
                        not (0.0001 < setting.value < 120)
                        or decimal.Decimal(str(setting.value)).as_tuple().exponent < -3
                    ):
                        raise AppValidationException(
                            "The FrameRate value range is between 0.001 - 120"
                        )
                    frame_mode = next(
                        filter(
                            lambda x: x.attribute == "FrameMode", self._project.settings
                        ),
                        None,
                    )
                    if not frame_mode:
                        self._project.settings.append(
                            SettingEntity(attribute="FrameMode", value=1)
                        )
                    else:
                        frame_mode.value = 1
                else:
                    raise AppValidationException("The FrameRate value should be float")

    def validate_project_name(self):
        if (
            len(
                set(self._project.name).intersection(
                    constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                )
            )
            > 0
        ):
            self._project.name = "".join(
                "_"
                if char in constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                else char
                for char in self._project.name
            )
            logger.warning(
                "New folder name has special characters. Special characters will be replaced by underscores."
            )
        condition = Condition("name", self._project.name, EQ)
        response = self._service_provider.projects.list(condition)
        if response.ok:
            for project in response.data:
                if project.name == self._project.name:
                    logger.error("There are duplicated names.")
                    raise AppValidationException(
                        f"Project name {self._project.name} is not unique. "
                        f"To use SDK please make project names unique."
                    )

    def execute(self):
        if self.is_valid():
            # new projects can only have the status of NotStarted
            self._project.status = constances.ProjectStatus.NotStarted.value
            response = self._service_provider.projects.create(self._project)
            if not response.ok:
                self._response.errors = response.error
            entity = response.data
            # create project doesn't store attachment data so need to update
            instructions_link = self._project.instructions_link
            if instructions_link:
                entity.instructions_link = instructions_link
                self._service_provider.projects.update(entity)
            self._response.data = entity
            data = {}
            # TODO delete
            # if self._settings:
            #     settings_repo = self._settings_repo(self._backend_service, entity)
            #     for setting in self._settings:
            #         for new_setting in settings_repo.get_all():
            #             if new_setting.attribute == setting.attribute:
            #                 setting_copy = copy.copy(setting)
            #                 setting_copy.id = new_setting.id
            #                 setting_copy.project_id = entity.uuid
            #                 settings_repo.update(setting_copy)
            #     data["settings"] = self._settings
            annotation_classes_mapping = {}
            if self._service_provider.annotation_classes:

                for annotation_class in self._project.classes:
                    annotation_classes_mapping[
                        annotation_class.id
                    ] = self._service_provider.annotation_classes.create_multiple(
                        entity, [annotation_class]
                    )
                data["classes"] = self._project.classes
            if self._project.workflows:
                set_workflow_use_case = SetWorkflowUseCase(
                    service_provider=self._service_provider,
                    steps=[i.dict() for i in self._project.workflows],
                    project=entity,
                )
                set_workflow_response = set_workflow_use_case.execute()
                data["workflows"] = (
                    GetWorkflowsUseCase(
                        project=self._project, service_provider=self._service_provider
                    )
                    .execute()
                    .data
                )
                if set_workflow_response.errors:
                    self._response.errors = set_workflow_response.errors

            logger.info(
                "Created project %s (ID %s) with type %s",
                self._response.data.name,
                self._response.data.id,
                constances.ProjectType.get_name(self._response.data.type),
            )
        return self._response


class DeleteProjectUseCase(BaseUseCase):
    def __init__(
        self,
        project_name: str,
        service_provider: BaseServiceProvider,
    ):

        super().__init__()
        self._project_name = project_name
        self._service_provider = service_provider

    def execute(self):
        use_case = GetProjectByNameUseCase(
            name=self._project_name, service_provider=self._service_provider
        )
        project_response = use_case.execute()
        if project_response.data:
            response = self._service_provider.projects.delete(project_response.data)
            if response.ok:
                logger.info("Successfully deleted project ")
            else:
                raise AppException("Couldn't delete project")


class UpdateProjectUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
    ):

        super().__init__()
        self._project = project
        self._service_provider = service_provider

    def validate_project_name(self):
        if self._project.name:
            if (
                len(
                    set(self._project.name).intersection(
                        constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    )
                )
                > 0
            ):
                self._project.name = "".join(
                    "_"
                    if char in constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    else char
                    for char in self._project.name
                )
                logger.warning(
                    "New folder name has special characters. Special characters will be replaced by underscores."
                )
            condition = Condition("name", self._project.name, EQ)
            response = self._service_provider.projects.list(condition)
            if response.ok:
                for project in response.data:
                    if project.name == self._project.name:
                        logger.error("There are duplicated names.")
                        raise AppValidationException(
                            f"Project name {self._project.name} is not unique. "
                            f"To use SDK please make project names unique."
                        )
            else:
                raise AppException(response.error)

    def execute(self):
        if self.is_valid():
            response = self._service_provider.projects.update(self._project)
            if not response.ok:
                self._response.errors = response.errors
            else:
                self._response.data = response.data
        return self._response


class CloneProjectUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        project_to_create: ProjectEntity,
        service_provider: BaseServiceProvider,
        include_annotation_classes: bool = True,
        include_settings: bool = True,
        include_workflow: bool = True,
        include_contributors: bool = False,
    ):
        super().__init__()
        self._project = project
        self._project_to_create = project_to_create
        self._service_provider = service_provider
        self._include_annotation_classes = include_annotation_classes
        self._include_settings = include_settings
        self._include_workflow = include_workflow
        self._include_contributors = include_contributors

    def validate_project_name(self):
        if self._project_to_create.name:
            if (
                len(
                    set(self._project_to_create.name).intersection(
                        constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    )
                )
                > 0
            ):
                self._project_to_create.name = "".join(
                    "_"
                    if char in constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    else char
                    for char in self._project_to_create.name
                )
                logger.warning(
                    "New folder name has special characters. Special characters will be replaced by underscores."
                )
            condition = Condition("name", self._project_to_create.name, EQ)
            for project in self._service_provider.projects.list(condition).data:
                if project.name == self._project_to_create.name:
                    logger.error("There are duplicated names.")
                    raise AppValidationException(
                        f"Project name {self._project_to_create.name} is not unique. "
                        f"To use SDK please make project names unique."
                    )

    def _copy_annotation_classes(
        self, annotation_classes_entity_mapping: dict, project: ProjectEntity
    ):
        annotation_classes = self._service_provider.annotation_classes.list(
            Condition("project_id", self._project.id, EQ)
        ).data
        for annotation_class in annotation_classes:
            annotation_class_copy = copy.copy(annotation_class)
            annotation_classes_entity_mapping[
                annotation_class.id
            ] = self._service_provider.annotation_classes.create(
                project.id, annotation_class_copy
            ).data

    def _copy_include_contributors(self, to_project: ProjectEntity):
        from_project = self._service_provider.projects.get(uuid=self._project.id).data
        users = []
        for user in from_project.users:
            users.append(
                {"user_id": user.get("user_id"), "user_role": user.get("user_role")}
            )

        for user in from_project.unverified_users:
            users.append(
                {"user_id": user.get("email"), "user_role": user.get("user_role")}
            )
        if users:
            self._service_provider.projects.share(to_project, users)

    def _copy_settings(self, to_project: ProjectEntity):
        new_settings = []
        for setting in self._service_provider.projects.list_settings(
            self._project
        ).data:
            if setting.attribute == "WorkflowType" and not self._include_workflow:
                continue
            for new_setting in self._service_provider.projects.list_settings(
                to_project
            ).data:
                if new_setting.attribute == setting.attribute:
                    setting_copy = copy.copy(setting)
                    setting_copy.id = new_setting.id
                    setting_copy.project_id = to_project.id
                    new_settings.append(setting_copy)

        self._service_provider.projects.set_settings(to_project, new_settings)

    def _copy_workflow(
        self, annotation_classes_entity_mapping: dict, to_project: ProjectEntity
    ):
        existing_workflow_ids = list(
            map(
                lambda i: i.id,
                self._service_provider.projects.list_workflows(to_project).data,
            )
        )
        for workflow in self._service_provider.projects.list_workflows(
            self._project
        ).data:
            workflow_data = copy.copy(workflow)
            workflow_data.project_id = to_project.id
            if workflow.class_id not in annotation_classes_entity_mapping:
                continue
            workflow_data.class_id = annotation_classes_entity_mapping[
                workflow.class_id
            ]["id"]
            self._service_provider.projects.set_workflow(to_project, workflow_data)
            workflows = self._service_provider.projects.list_workflows(to_project).data
            new_workflow = next(
                (
                    work_flow
                    for work_flow in workflows
                    if work_flow.id not in existing_workflow_ids
                ),
                None,
            )
            workflow_attributes = []
            for attribute in workflow_data.attribute:
                for annotation_attribute in annotation_classes_entity_mapping[
                    workflow.class_id
                ]["attribute_groups"]:
                    if (
                        attribute["attribute"]["attribute_group"]["name"]
                        == annotation_attribute["name"]
                    ):
                        for annotation_attribute_value in annotation_attribute[
                            "attributes"
                        ]:
                            if (
                                annotation_attribute_value.get("name")
                                == attribute["attribute"]["name"]
                            ):
                                workflow_attributes.append(
                                    {
                                        "workflow_id": new_workflow.id,
                                        "attribute_id": annotation_attribute_value[
                                            "id"
                                        ],
                                    }
                                )
                                break
            if workflow_attributes:
                self._service_provider.projects.set_project_workflow_attributes(
                    project=to_project,
                    attributes=workflow_attributes,
                )

    def execute(self):
        if self.is_valid():
            if self._project_to_create.type in (
                constances.ProjectType.PIXEL.value,
                constances.ProjectType.VECTOR.value,
            ):
                self._project_to_create.upload_state = (
                    constances.UploadState.INITIAL.value
                )

            self._project_to_create.status = constances.ProjectStatus.NotStarted.value

            project = self._service_provider.projects.create(
                self._project_to_create
            ).data
            logger.info(
                f"Created project {self._project_to_create.name} with type"
                f" {constances.ProjectType.get_name(self._project_to_create.type)}."
            )
            # annotation_classes_entity_mapping = defaultdict(dict)
            annotation_classes_entity_mapping = defaultdict(AnnotationClassEntity)
            annotation_classes_created = False
            if self._include_settings:
                logger.info(
                    f"Cloning settings from {self._project.name} to {self._project_to_create.name}."
                )
                try:
                    self._copy_settings(project)
                except (AppException, RequestException) as e:
                    logger.info(
                        f"Failed to clone settings from {self._project.name} to {self._project_to_create.name}."
                    )
                    logger.debug(str(e), exc_info=True)

            if self._include_contributors:
                logger.info(
                    f"Cloning contributors from {self._project.name} to {self._project_to_create.name}."
                )
                try:
                    self._copy_include_contributors(project)
                except (AppException, RequestException) as e:
                    logger.warning(
                        f"Failed to clone contributors from {self._project.name} to {self._project_to_create.name}."
                    )
                    logger.debug(str(e), exc_info=True)

            if self._include_annotation_classes:
                logger.info(
                    f"Cloning annotation classes from {self._project.name} to {self._project_to_create.name}."
                )
                try:
                    self._copy_annotation_classes(
                        annotation_classes_entity_mapping, project
                    )
                    annotation_classes_created = True
                except (AppException, RequestException) as e:
                    logger.warning(
                        f"Failed to clone annotation classes from {self._project.name} to {self._project_to_create.name}."
                    )
                    logger.debug(str(e), exc_info=True)

            if self._include_workflow:
                if self._project.type in (
                    constances.ProjectType.DOCUMENT.value,
                    constances.ProjectType.VIDEO.value,
                ):
                    logger.warning(
                        "Workflow copy is deprecated for "
                        f"{constances.ProjectType.get_name(self._project_to_create.type)} projects."
                    )
                elif not annotation_classes_created:
                    logger.info(
                        f"Skipping the workflow clone from {self._project.name} to {self._project_to_create.name}."
                    )
                else:
                    logger.info(
                        f"Cloning workflow from {self._project.name} to {self._project_to_create.name}."
                    )
                    try:
                        self._copy_workflow(annotation_classes_entity_mapping, project)
                    except (AppException, RequestException) as e:
                        logger.warning(
                            f"Failed to workflow from {self._project.name} to {self._project_to_create.name}."
                        )
                        logger.debug(str(e), exc_info=True)

            self._response.data = self._service_provider.projects.get(project.id).data
        return self._response


class UnShareProjectUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
        user_id: str,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._project = project
        self._user_id = user_id

    def execute(self):
        self._response.data = self._service_provider.projects.un_share(
            project=self._project,
            user_id=self._user_id,
        ).data
        logger.info(
            f"Unshared project {self._project.name} from user ID {self._user_id}"
        )
        return self._response


class GetSettingsUseCase(BaseUseCase):
    def __init__(self, project: ProjectEntity, service_provider: BaseServiceProvider):
        super().__init__()
        self._project = project
        self._service_provider = service_provider

    def execute(self):
        self._response.data = self._service_provider.projects.list_settings(
            self._project
        ).data
        return self._response


class GetWorkflowsUseCase(BaseUseCase):
    def __init__(self, project: ProjectEntity, service_provider: BaseServiceProvider):
        super().__init__()
        self._project = project
        self._service_provider = service_provider

    def validate_project_type(self):
        if self._project.type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.type]
            )

    def execute(self):
        if self.is_valid():
            data = []
            workflows = self._service_provider.projects.list_workflows(
                self._project
            ).data
            for workflow in workflows:
                workflow_data = workflow.dict()
                annotation_classes = self._service_provider.annotation_classes.list(
                    Condition("project_id", self._project.id, EQ)
                ).data
                for annotation_class in annotation_classes:
                    if annotation_class.id == workflow.class_id:
                        workflow_data["className"] = annotation_class.name
                        break
                data.append(workflow_data)
            self._response.data = data
        return self._response


class UpdateSettingsUseCase(BaseUseCase):
    def __init__(
        self,
        to_update: List,
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._to_update = to_update
        self._project = project

    def validate_image_quality(self):
        for setting in self._to_update:
            if setting["attribute"].lower() == "imagequality" and isinstance(
                setting["value"], str
            ):
                setting["value"] = constances.ImageQuality.get_value(setting["value"])
                return

    def validate_project_type(self):
        for attribute in self._to_update:
            if attribute.get(
                "attribute", ""
            ) == "ImageQuality" and self._project.type in [
                constances.ProjectType.VIDEO.value,
                constances.ProjectType.DOCUMENT.value,
            ]:
                raise AppValidationException(
                    constances.DEPRICATED_DOCUMENT_VIDEO_MESSAGE
                )

    def execute(self):
        if self.is_valid():
            old_settings = self._service_provider.projects.list_settings(
                self._project
            ).data
            attr_id_mapping = {}
            for setting in old_settings:
                attr_id_mapping[setting.attribute] = setting.id

            new_settings_to_update = []
            for new_setting in self._to_update:
                new_settings_to_update.append(
                    SettingEntity(
                        id=attr_id_mapping[new_setting["attribute"]],
                        attribute=new_setting["attribute"],
                        value=new_setting["value"],
                    )
                )

            response = self._service_provider.projects.set_settings(
                project=self._project,
                data=new_settings_to_update,
            )
            if response.ok:
                self._response.data = response.data
            else:
                self._response.errors = response.error
        return self._response


class GetProjectImageCountUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        with_all_sub_folders: bool = False,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._project = project
        self._folder = folder
        self._with_all_sub_folders = with_all_sub_folders

    def validate_user_input(self):
        if not self._folder.name == "root" and self._with_all_sub_folders:
            raise AppValidationException("The folder does not contain any sub-folders.")

    def validate_project_type(self):
        if self._project.type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.type]
            )

    def execute(self):
        if self.is_valid():
            data = self._service_provider.get_project_images_count(self._project).data
            count = 0
            if self._folder.name == "root":
                count += data["images"]["count"]
                if self._with_all_sub_folders:
                    for i in data["folders"]["data"]:
                        count += i["imagesCount"]
            else:
                for i in data["folders"]["data"]:
                    if i["id"] == self._folder.id:
                        count = i["imagesCount"]

            self._response.data = count
        return self._response


class SetWorkflowUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        steps: list,
        project: ProjectEntity,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._steps = steps
        self._project = project

    def validate_project_type(self):
        if self._project.type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.type]
            )

    def execute(self):
        if self.is_valid():
            annotation_classes = self._service_provider.annotation_classes.list(
                Condition("project_id", self._project.id, EQ)
            ).data
            annotation_classes_map = {}
            annotations_classes_attributes_map = {}
            for annotation_class in annotation_classes:
                annotation_classes_map[annotation_class.name] = annotation_class.id
                for attribute_group in annotation_class.attribute_groups:
                    for attribute in attribute_group.attributes:
                        annotations_classes_attributes_map[
                            f"{annotation_class.name}__{attribute_group.name}__{attribute.name}"
                        ] = attribute.id

            for step in [step for step in self._steps if "className" in step]:
                if step.get("id"):
                    del step["id"]
                step["class_id"] = annotation_classes_map.get(step["className"], None)
                if not step["class_id"]:
                    raise AppException(
                        "Annotation class not found in set_project_workflow."
                    )

            self._service_provider.projects.set_workflows(
                project=self._project,
                steps=self._steps,
            )
            existing_workflows = self._service_provider.projects.list_workflows(
                self._project
            ).data
            existing_workflows_map = {}
            for workflow in existing_workflows:
                existing_workflows_map[workflow.step] = workflow.id

            req_data = []
            for step in self._steps:
                annotation_class_name = step["className"]
                for attribute in step["attribute"]:
                    attribute_name = attribute["attribute"]["name"]
                    attribute_group_name = attribute["attribute"]["attribute_group"][
                        "name"
                    ]
                    if not annotations_classes_attributes_map.get(
                        f"{annotation_class_name}__{attribute_group_name}__{attribute_name}",
                        None,
                    ):
                        raise AppException(
                            "Attribute group name or attribute name not found in set_project_workflow."
                        )

                    if not existing_workflows_map.get(step["step"], None):
                        raise AppException("Couldn't find step in workflow")
                    req_data.append(
                        {
                            "workflow_id": existing_workflows_map[step["step"]],
                            "attribute_id": annotations_classes_attributes_map[
                                f"{annotation_class_name}__{attribute_group_name}__{attribute_name}"
                            ],
                        }
                    )
            self._service_provider.projects.set_project_workflow_attributes(
                project=self._project,
                attributes=req_data,
            )
        return self._response


class GetTeamUseCase(BaseUseCase):
    def __init__(self, service_provider: BaseServiceProvider, team_id: int):
        super().__init__()
        self._service_provider = service_provider
        self._team_id = team_id

    def execute(self):
        try:
            response = self._service_provider.get_team(self._team_id)
            if not response.ok:
                raise AppException(response.error)
            self._response.data = response.data
        except Exception:
            raise AppException("Can't get team data.") from None
        return self._response


class SearchContributorsUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        team_id: int,
        condition: Condition = None,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._team_id = team_id
        self._condition = condition

    def execute(self):
        res = self._service_provider.search_team_contributors(self._condition)
        self._response.data = res.data
        return self._response


class AddContributorsToProject(BaseUserBasedUseCase):
    """
    Returns tuple of lists (added, skipped)
    """

    def __init__(
        self,
        reporter: Reporter,
        team: TeamEntity,
        project: ProjectEntity,
        emails: list,
        role: str,
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter, emails)
        self._team = team
        self._project = project
        self._role = role
        self._service_provider = service_provider

    @property
    def user_role(self):
        return constances.UserRole.get_value(self._role)

    def validate_emails(self):
        emails = list(set(self._emails))
        len_unique, len_provided = len(emails), len(self._emails)
        if len_unique < len_provided:
            logger.info(
                f"Dropping duplicates. Found {len_unique}/{len_provided} unique users."
            )
        self._emails = emails

    def execute(self):
        if self.is_valid():
            team_users = set()
            project_users = {user["user_id"] for user in self._project.users}
            for user in self._team.users:
                if user.user_role > constances.UserRole.ADMIN.value:
                    team_users.add(user.email)
            # collecting pending team users which is not admin
            for user in self._team.pending_invitations:
                if user["user_role"] > constances.UserRole.ADMIN.value:
                    team_users.add(user["email"])
            # collecting pending project users which is not admin
            for user in self._project.unverified_users:
                if user["user_role"] > constances.UserRole.ADMIN.value:
                    project_users.add(user["email"])

            to_add = list(team_users.intersection(self._emails) - project_users)
            to_skip = list(set(self._emails).difference(to_add))

            if to_skip:
                self.reporter.log_warning(
                    f"Skipped {len(to_skip)}/{len(self._emails)} "
                    "contributors that are out of the team scope or already have access to the project."
                )
            if to_add:
                response = self._service_provider.projects.share(
                    project=self._project,
                    users=[
                        dict(user_id=user_id, user_role=self.user_role)
                        for user_id in to_add
                    ],
                )
                if response and not response.data.get("invalidUsers"):
                    self.reporter.log_info(
                        f"Added {len(to_add)}/{len(self._emails)} "
                        f"contributors to the project {self._project.name} with the {self._role} role."
                    )
            self._response.data = to_add, to_skip
            return self._response


class InviteContributorsToTeam(BaseUserBasedUseCase):
    """
    Returns tuple of lists (added, skipped)
    """

    def __init__(
        self,
        reporter: Reporter,
        team: TeamEntity,
        emails: list,
        set_admin: bool,
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter, emails)
        self._team = team
        self._set_admin = set_admin
        self._service_provider = service_provider

    def execute(self):
        if self.is_valid():
            team_users = {user.email for user in self._team.users}
            # collecting pending team users
            team_users.update(
                {user["email"] for user in self._team.pending_invitations}
            )

            emails = set(self._emails)

            to_skip = list(emails.intersection(team_users))
            to_add = list(emails.difference(to_skip))
            invited, failed = [], to_skip
            if to_skip:
                self.reporter.log_warning(
                    f"Found {len(to_skip)}/{len(self._emails)} existing members of the team."
                )
            if to_add:
                response = self._service_provider.invite_contributors(
                    team_id=self._team.id,
                    # REMINDER UserRole.VIEWER is the contributor for the teams
                    team_role=constances.UserRole.ADMIN.value
                    if self._set_admin
                    else constances.UserRole.VIEWER.value,
                    emails=to_add,
                )
                invited, failed = (
                    response.data["success"]["emails"],
                    response.data["failed"]["emails"],
                )
                if invited:
                    self.reporter.log_info(
                        f"Sent team {'admin' if self._set_admin else 'contributor'} invitations"
                        f" to {len(invited)}/{len(self._emails)} users."
                    )
                if failed:
                    to_skip = set(to_skip)
                    to_skip.update(set(failed))
                    self.reporter.log_info(
                        f"Skipped team {'admin' if self._set_admin else 'contributor'} "
                        f"invitations for {len(failed)}/{len(self._emails)} users."
                    )
            self._response.data = invited, list(to_skip)
            return self._response


class ListSubsetsUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._service_provider = service_provider

    def validate_arguments(self):
        response = self._service_provider.validate_saqul_query(self._project, "_")
        if not response.ok:
            raise AppException(response.error)

    def execute(self) -> Response:
        if self.is_valid():
            sub_sets_response = self._service_provider.subsets.list(
                project=self._project
            )
            if sub_sets_response.ok:
                self._response.data = sub_sets_response.data
            else:
                self._response.data = []

        return self._response
