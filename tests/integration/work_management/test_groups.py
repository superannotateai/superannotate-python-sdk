from superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestGroups(BaseTestCase):
    PROJECT_NAME = "TestGroups"
    PROJECT_TYPE = "Vector"
    GROUP_NAME = "TestGroup"

    def setUp(self):
        super().setUp()
        # Get available team users for testing
        team_users = sa.list_users()
        assert len(team_users) > 0
        
        # Find contributors for testing
        self.contributors = [
            u for u in team_users
            if u["role"] == "Contributor" and u["state"] == "Confirmed"
        ][:2]  # Take first 2 contributors
        
        assert len(self.contributors) >= 1, "Need at least 1 contributor for testing"
        
        self.contributor_emails = [u["email"] for u in self.contributors]

    def test_create_group_with_contributors(self):
        group = sa.groups.create(self.GROUP_NAME, self.contributor_emails)
        
        assert group.name == self.GROUP_NAME
        assert len(group.contributors) == len(self.contributor_emails)
        assert all(email in group.contributors for email in self.contributor_emails)
        assert group.id is not None
        assert group.created_at is not None

    def test_create_group_without_contributors(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_empty")
        
        assert group.name == f"{self.GROUP_NAME}_empty"
        assert len(group.contributors) == 0
        assert group.id is not None

    def test_create_duplicate_group_name_raises_exception(self):
        sa.groups.create(f"{self.GROUP_NAME}_duplicate")
        
        with self.assertRaises(Exception):
            sa.groups.create(f"{self.GROUP_NAME}_duplicate")

    def test_list_groups(self):
        # Create a test group
        created_group = sa.groups.create(f"{self.GROUP_NAME}_list", self.contributor_emails[:1])
        
        groups = sa.groups.list()
        
        assert len(groups) > 0
        group_names = [g.name for g in groups]
        assert f"{self.GROUP_NAME}_list" in group_names
        
        # Find our created group
        our_group = next(g for g in groups if g.name == f"{self.GROUP_NAME}_list")
        assert our_group.id == created_group.id
        assert len(our_group.contributors) == 1

    def test_add_contributor_to_group(self):
        if len(self.contributors) < 2:
            self.skipTest("Need at least 2 contributors for this test")
            
        group = sa.groups.create(f"{self.GROUP_NAME}_add", [self.contributor_emails[0]])
        initial_count = len(group.contributors)
        
        group.add_contributor([self.contributor_emails[1]])
        
        assert len(group.contributors) == initial_count + 1
        assert self.contributor_emails[1] in group.contributors

    def test_remove_contributor_from_group(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_remove", self.contributor_emails)
        initial_count = len(group.contributors)
        
        group.remove_contributors([self.contributor_emails[0]])
        
        assert len(group.contributors) == initial_count - 1
        assert self.contributor_emails[0] not in group.contributors

    def test_remove_contributor_from_group_and_team(self):
        if len(self.contributors) < 1:
            self.skipTest("Need at least 1 contributor for this test")
            
        group = sa.groups.create(f"{self.GROUP_NAME}_remove_team", [self.contributor_emails[0]])
        
        # This should remove from group and team
        group.remove_contributors([self.contributor_emails[0]], remove_from_team=True)
        
        assert self.contributor_emails[0] not in group.contributors

    def test_rename_group(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_rename")
        new_name = f"{self.GROUP_NAME}_renamed"
        
        group.rename(new_name)
        
        assert group.name == new_name

    def test_rename_group_to_existing_name_raises_exception(self):
        sa.groups.create(f"{self.GROUP_NAME}_existing")
        group = sa.groups.create(f"{self.GROUP_NAME}_to_rename")
        
        with self.assertRaises(Exception):
            group.rename(f"{self.GROUP_NAME}_existing")

    def test_share_project_with_all_group_members(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_share", self.contributor_emails[:1])
        
        # Share project with all group members (default behavior)
        group.share(project=self.PROJECT_NAME, role="Annotator")
        
        # Verify the user has access to the project
        project_users = sa.list_users(project=self.PROJECT_NAME)
        project_emails = [u["email"] for u in project_users]
        assert self.contributor_emails[0] in project_emails

    def test_share_project_with_specific_members(self):
        if len(self.contributors) < 2:
            self.skipTest("Need at least 2 contributors for this test")
            
        group = sa.groups.create(f"{self.GROUP_NAME}_share_specific", self.contributor_emails)
        
        # Share with only one specific member
        group.share(
            project=self.PROJECT_NAME,
            role="QA",
            contributors=[self.contributor_emails[0]]
        )
        
        project_users = sa.list_users(project=self.PROJECT_NAME)
        project_emails = [u["email"] for u in project_users]
        assert self.contributor_emails[0] in project_emails

    def test_share_project_with_folder_scope(self):
        # Create a folder first
        folder_name = "test_folder"
        sa.create_folder(self.PROJECT_NAME, folder_name)
        
        group = sa.groups.create(f"{self.GROUP_NAME}_folder_share", self.contributor_emails[:1])
        
        group.share(
            project=self.PROJECT_NAME,
            role="Annotator",
            scope=[folder_name]
        )
        
        # Verify access was granted
        project_users = sa.list_users(project=self.PROJECT_NAME)
        project_emails = [u["email"] for u in project_users]
        assert self.contributor_emails[0] in project_emails

    def test_share_invalid_project_raises_exception(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_invalid_project")
        
        with self.assertRaises(Exception):
            group.share(project="NonExistentProject", role="Annotator")

    def test_share_invalid_role_raises_exception(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_invalid_role")
        
        with self.assertRaises(Exception):
            group.share(project=self.PROJECT_NAME, role="InvalidRole")

    def test_group_to_dict(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_dict", self.contributor_emails[:1])
        
        group_dict = group.to_dict()
        
        assert isinstance(group_dict, dict)
        assert group_dict["id"] == group.id
        assert group_dict["name"] == group.name
        assert group_dict["contributors"] == group.contributors
        assert group_dict["created_at"] == group.created_at
        assert group_dict["projects"] == group.projects

    def test_delete_group(self):
        group_name = f"{self.GROUP_NAME}_delete"
        sa.groups.create(group_name)
        
        sa.groups.delete(group_name)
        
        # Verify group is deleted
        groups = sa.groups.list()
        group_names = [g.name for g in groups]
        assert group_name not in group_names

    def test_delete_group_and_remove_members_from_team(self):
        group_name = f"{self.GROUP_NAME}_delete_team"
        sa.groups.create(group_name, self.contributor_emails[:1])
        
        sa.groups.delete(group_name, remove_from_team=True)
        
        # Verify group is deleted
        groups = sa.groups.list()
        group_names = [g.name for g in groups]
        assert group_name not in group_names

    def test_delete_nonexistent_group_raises_exception(self):
        with self.assertRaises(Exception):
            sa.groups.delete("NonExistentGroup")

    def test_add_nonexistent_contributor_raises_exception(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_invalid_contributor")
        
        with self.assertRaises(Exception):
            group.add_contributor(["nonexistent@example.com"])

    def test_remove_nonexistent_contributor_raises_exception(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_remove_invalid")
        
        with self.assertRaises(Exception):
            group.remove_contributors(["nonexistent@example.com"])

    def test_share_with_nonexistent_folder_raises_exception(self):
        group = sa.groups.create(f"{self.GROUP_NAME}_invalid_folder")
        
        with self.assertRaises(Exception):
            group.share(
                project=self.PROJECT_NAME,
                role="Annotator",
                scope=["nonexistent_folder"]
            )