import os
import time
from typing import List
import contextvars
from functools import lru_cache

from tests import DATA_SET_PATH
from tests.base import BaseApplicationTestCase
from src.superannotate import SAClient, AppException

sa = SAClient()

attached_item_names = contextvars.ContextVar('attached_item_names')
attached_items_status = contextvars.ContextVar('attached_items_status')
contributors_role = contextvars.ContextVar('contributors_role')
annotation_classes_count = contextvars.ContextVar('annotation_classes_count')


class TestWorkflow(BaseApplicationTestCase):
    PROJECT_NAME = 'TestWorkflow'

    CLASSES_PATH = "sample_project_vector/classes/classes.json"
    ANNOTATIONS_PATH = "sample_project_vector"
    PROJECT_TYPE = "GenAi"

    @property
    def classes_path(self):
        return os.path.join(DATA_SET_PATH, self.CLASSES_PATH)

    @property
    def annotations_path(self):
        return os.path.join(DATA_SET_PATH, self.ANNOTATIONS_PATH)

    @lru_cache()
    def get_not_admin_contributor_emails(self) -> List[str]:
        contributor_emails = []
        for i in sa.search_team_contributors():
            if i['user_role'] != 2:  # skipping admins etc
                contributor_emails.append(i['email'])
        return contributor_emails

    def step_1_add_contributors(self):
        contributor_emails = self.get_not_admin_contributor_emails()
        assert len(contributor_emails) > 0, "for the test there should be more then 1 contributor"
        # Give the backend time to think
        time.sleep(3)
        contributors_role.set("Annotator")
        added, skipped, = sa.add_contributors_to_project(self.PROJECT_NAME, contributor_emails, "Annotator")
        assert len(skipped) == 0
        assert len(added) == len(contributor_emails)


    def step_3_attach_items(self):
        name_prefix, count = 'example_image_', 4
        items_to_attach = [
            {"name": f"{name_prefix}{i}.jpg", "url": f"url_{i}"}
            for i in range(1, count + 1)
        ]
        attached_item_names.set([i['name'] for i in items_to_attach])
        attached_items_status.set("Completed")
        uploaded, _, __ = sa.attach_items(
            self.PROJECT_NAME,
            items_to_attach,  # noqa
            annotation_status="Completed"
        )
        assert len(uploaded) == count
        items = sa.search_items(self.PROJECT_NAME)
        assert all(i['annotation_status'] == 'Completed' for i in items)

    def step_4_create_annotation_classes(self):
        created = sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)
        annotation_classes_count.set(4)
        assert len(created) == 4

    def step_5_upload_annotations(self):
        uploaded, _, __ = sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, self.annotations_path, keep_status=True
            )
        attached_items_count = len(attached_item_names.get())
        assert len(uploaded) == attached_items_count
        #  assert that all items have a status of "attached_items_status"
        items = sa.search_items(self.PROJECT_NAME, annotation_status=attached_items_status.get())
        assert len(items) == attached_items_count

    def step_6_get_annotations(self):
        annotations = sa.get_annotations(self.PROJECT_NAME)
        assert len(annotations) == len(attached_item_names.get())
        assert all(i['metadata']['status'] == attached_items_status.get() for i in annotations)

    def step_7_assign_item(self):
        item = attached_item_names.get()[0]
        user = self.get_not_admin_contributor_emails()[0]
        sa.assign_items(self.PROJECT_NAME, [item], user)
        item_data = sa.get_item_metadata(self.PROJECT_NAME, item)
        if contributors_role.get() in ("Annotator", 'QA'):
            assert item_data[f"{contributors_role.get().lower()}_email"] == user
        assert len(item_data['assignments']) == 1
        assert item_data['assignments'][0]['user_role'] == contributors_role.get()

    def step_8_unassign_item(self):
        item = attached_item_names.get()[0]
        sa.unassign_items(self.PROJECT_NAME, [item])
        item_data = sa.get_item_metadata(self.PROJECT_NAME, item)
        if contributors_role.get() in ("Annotator", 'QA'):
            assert item_data[f"{contributors_role.get().lower()}_email"] is None
        assert len(item_data['assignments']) == 0

    def step_999_clone(self):
        new_name = 'step_clone'
        try:
            sa.delete_project(new_name)
        except AppException:
            ...
        project = sa.clone_project(new_name, self.PROJECT_NAME, copy_contributors=True)
        contributors = self.get_not_admin_contributor_emails()
        assert len(contributors) == len(project['users'])
        assert all(i['user_role'] == contributors_role.get() for i in project['users'])
        assert len(project['classes']) == annotation_classes_count.get()


    def _steps(self):
        for name in dir(self):
            if name.startswith("step"):
                yield name, getattr(self, name)

    def test_steps(self):
        for name, step in self._steps():
            try:
                step()
            except Exception as e:
                self.fail("{} failed ({}: {})".format(step, type(e), e))
