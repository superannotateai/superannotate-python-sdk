import decimal
import logging
from collections import defaultdict
from typing import List

import lib.core as constances
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import ContributorEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import SettingEntity
from lib.core.entities import TeamEntity
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases.base import BaseUseCase
from lib.core.usecases.base import BaseUserBasedUseCase


logger = logging.getLogger("sa")


class GetProjectByIDUseCase(BaseUseCase):
    def __init__(self, project_id, service_provider):
        self._project_id = project_id
        self._service_provider = service_provider
        super().__init__()

    def execute(self):
        try:

            self._response.data = self._service_provider.projects.get_by_id(
                project_id=self._project_id
            )

        except AppException as e:
            self._response.errors = e
        else:
            if not self._response.data.data:
                self._response.errors = AppException(
                    "Either the specified project does not exist or you do not have permission to view it"
                )

        return self._response


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
                self._response.errors = response.error
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


class GetProjectMetaDataUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
        include_annotation_classes: bool,
        include_settings: bool,
        include_workflow: bool,
        include_contributors: bool,
        include_complete_image_count: bool,
    ):
        super().__init__()
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
            project.root_folder_completed_items_count = root_completed_count
            project.completed_items_count = total_completed_count
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
                try:
                    setting.value = float(setting.value)
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
                except ValueError:
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
            if not entity:
                self._response.errors = AppException("Failed to create project.")
                return self._response
            self._response.data = entity
            data = {}
            # TODO delete if create_from_metadata deleted
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
                f"Created project {entity.name} (ID {entity.id}) "
                f"with type {constances.ProjectType.get_name(self._response.data.type)}."
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
                self._response.errors = response.error
            else:
                self._response.data = response.data
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
                    raise AppException("Annotation class not found.")
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
                            f"Attribute group name or attribute name not found {attribute_group_name}."
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
            raise AppException(
                "Unable to retrieve team data. Please verify your credentials."
            ) from None
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


class AddContributorsToProject(BaseUseCase):
    """
    Returns tuple of lists (added, skipped)
    """

    def __init__(
        self,
        team: TeamEntity,
        project: ProjectEntity,
        contributors: List[ContributorEntity],
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._team = team
        self._project = project
        self._contributors = contributors
        self._service_provider = service_provider

    def validate_emails(self):
        email_entity_map = {}
        for c in self._contributors:
            email_entity_map[c.user_id] = c
        len_unique, len_provided = len(email_entity_map), len(self._contributors)
        if len_unique < len_provided:
            logger.info(
                f"Dropping duplicates. Found {len_unique}/{len_provided} unique users."
            )
        self._contributors = email_entity_map.values()

    def execute(self):
        if self.is_valid():
            team_users = set()
            project_users = {user.user_id for user in self._project.users}
            for user in self._team.users:
                if user["user_role"] > constances.UserRole.ADMIN.value:
                    team_users.add(user["email"])
            # collecting pending team users which is not admin
            for user in self._team.pending_invitations:
                if user["user_role"] > constances.UserRole.ADMIN.value:
                    team_users.add(user["email"])
            # collecting pending project users which is not admin
            for user in self._project.unverified_users:
                if user["user_role"] > constances.UserRole.ADMIN.value:
                    project_users.add(user["email"])

            role_email_map = defaultdict(list)
            to_skip = []
            to_add = []
            for contributor in self._contributors:
                role_email_map[contributor.user_role].append(contributor.user_id)
            for role, emails in role_email_map.items():
                _to_add = list(team_users.intersection(emails) - project_users)
                to_add.extend(_to_add)
                to_skip.extend(list(set(emails).difference(_to_add)))
                if _to_add:
                    response = self._service_provider.projects.share(
                        project=self._project,
                        users=[
                            dict(
                                user_id=user_id,
                                user_role=role.value,
                            )
                            for user_id in _to_add
                        ],
                    )
                    if not response.ok:
                        self._response.errors = AppException(response.error)
                        return self._response
                    if response and not response.data.get("invalidUsers"):
                        logger.info(
                            f"Added {len(_to_add)}/{len(emails)} "
                            f"contributors to the project {self._project.name} with the {role.name} role."
                        )

            if to_skip:
                logger.warning(
                    f"Skipped {len(to_skip)}/{len(self._contributors)} "
                    "contributors that are out of the team scope or already have access to the project."
                )
            self._response.data = to_add, to_skip
            return self._response


class InviteContributorsToTeam(BaseUserBasedUseCase):
    """
    Returns tuple of lists (added, skipped)
    """

    def __init__(
        self,
        team: TeamEntity,
        emails: list,
        set_admin: bool,
        service_provider: BaseServiceProvider,
    ):
        super().__init__(emails)
        self._team = team
        self._set_admin = set_admin
        self._service_provider = service_provider

    def execute(self):
        if self.is_valid():
            team_users = {user["email"] for user in self._team.users}
            # collecting pending team users
            team_users.update(
                {user["email"] for user in self._team.pending_invitations}
            )

            emails = set(self._emails)

            to_skip = list(emails.intersection(team_users))
            to_add = list(emails.difference(to_skip))
            invited, failed = [], to_skip
            if to_skip:
                logger.warning(
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
                    logger.info(
                        f"Sent team {'admin' if self._set_admin else 'contributor'} invitations"
                        f" to {len(invited)}/{len(self._emails)} users."
                    )
                if failed:
                    to_skip = set(to_skip)
                    to_skip.update(set(failed))
                    logger.info(
                        f"Skipped team {'admin' if self._set_admin else 'contributor'} "
                        f"invitations for {len(failed)}/{len(self._emails)} users."
                    )
            self._response.data = invited, list(to_skip)
            return self._response


class ListSubsetsUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
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
