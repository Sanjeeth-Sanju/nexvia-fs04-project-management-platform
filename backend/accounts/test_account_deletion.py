from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Workspace,
    WorkspaceMembership,
    Project,
    Board,
    Issue,
    IssueComment,
    IssueAttachment,
)

User = get_user_model()

PASSWORD = "StrongTestPassword!2026"
CONFIRMATION = "DELETE MY ACCOUNT"


class AccountDeletionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="deletion_user",
            email="deletion@example.com",
            password=PASSWORD,
        )
        self.client.force_authenticate(user=self.user)

        self.impact_url = reverse("account-deletion-impact")
        self.confirm_url = reverse("account-deletion-confirm")

    def create_workspace(self, name, slug, user, role):
        workspace = Workspace.objects.create(name=name, slug=slug)
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=user,
            role=role,
        )
        return workspace

    def create_issue(self, workspace, key="TEST"):
        project = Project.objects.create(
            workspace=workspace,
            name=f"{workspace.name} Project",
            key=key,
        )
        board = Board.objects.create(
            project=project,
            name="Main Board",
        )
        issue = Issue.objects.create(
            project=project,
            board=board,
            title="Test issue",
        )
        return project, issue

    def confirm_deletion(self, password=PASSWORD, phrase=CONFIRMATION):
        return self.client.post(
            self.confirm_url,
            {
                "current_password": password,
                "confirmation": phrase,
            },
            format="json",
        )

    def test_impact_preview_separates_owned_and_other_workspaces(self):
        owned = self.create_workspace(
            "Owned Workspace", "owned-workspace", self.user, "owner"
        )
        other = self.create_workspace(
            "Other Workspace", "other-workspace", self.user, "admin"
        )

        teammate = User.objects.create_user(
            username="teammate",
            password=PASSWORD,
        )
        WorkspaceMembership.objects.create(
            workspace=owned,
            user=teammate,
            role="member",
        )

        response = self.client.get(self.impact_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["owned_workspace_count"], 1)
        self.assertEqual(response.data["leaving_workspace_count"], 1)
        self.assertEqual(
            response.data["owned_workspaces"][0]["id"],
            owned.id,
        )
        self.assertEqual(
            response.data["owned_workspaces"][0]["other_member_count"],
            1,
        )
        self.assertEqual(
            response.data["leaving_workspaces"][0]["id"],
            other.id,
        )
        self.assertEqual(
            response.data["leaving_workspaces"][0]["role"],
            "admin",
        )
        self.assertEqual(
            response.data["confirmation_phrase"],
            CONFIRMATION,
        )

    def test_owner_deletion_removes_owned_workspace_but_preserves_shared_history(self):
        owned = self.create_workspace(
            "Owned Workspace", "owned-workspace-delete", self.user, "owner"
        )
        shared = self.create_workspace(
            "Shared Workspace", "shared-workspace-preserve", self.user, "member"
        )

        other_user = User.objects.create_user(
            username="other_owner",
            password=PASSWORD,
        )
        WorkspaceMembership.objects.create(
            workspace=shared,
            user=other_user,
            role="owner",
        )

        _, owned_issue = self.create_issue(owned, "OWN")
        _, shared_issue = self.create_issue(shared, "SHR")

        comment = IssueComment.objects.create(
            issue=shared_issue,
            author=self.user,
            body="Keep this shared comment",
        )
        attachment = IssueAttachment.objects.create(
            issue=shared_issue,
            uploaded_by=self.user,
            file="issue_attachments/shared-file.txt",
            filename="shared-file.txt",
        )

        user_id = self.user.pk
        response = self.confirm_deletion()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(pk=user_id).exists())

        self.assertFalse(Workspace.objects.filter(pk=owned.pk).exists())
        self.assertFalse(Issue.objects.filter(pk=owned_issue.pk).exists())

        self.assertTrue(Workspace.objects.filter(pk=shared.pk).exists())
        self.assertTrue(Issue.objects.filter(pk=shared_issue.pk).exists())

        comment.refresh_from_db()
        attachment.refresh_from_db()

        self.assertIsNone(comment.author)
        self.assertEqual(comment.body, "Keep this shared comment")
        self.assertIsNone(attachment.uploaded_by)
        self.assertEqual(attachment.filename, "shared-file.txt")

        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace=shared,
                user=other_user,
                role="owner",
            ).exists()
        )
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                workspace=shared,
                user_id=user_id,
            ).exists()
        )

        self.assertEqual(response.data["deleted_workspace_count"], 1)
        self.assertEqual(response.data["left_workspace_count"], 1)

    def test_admin_and_member_deletion_leave_workspace_data_intact(self):
        for role in ("admin", "member"):
            with self.subTest(role=role):
                user = User.objects.create_user(
                    username=f"{role}_deletion_user",
                    password=PASSWORD,
                )
                client = APIClient()
                client.force_authenticate(user=user)

                workspace = Workspace.objects.create(
                    name=f"{role.title()} Workspace",
                    slug=f"{role}-workspace-preserved",
                )
                owner = User.objects.create_user(
                    username=f"{role}_workspace_owner",
                    password=PASSWORD,
                )

                WorkspaceMembership.objects.create(
                    workspace=workspace,
                    user=owner,
                    role="owner",
                )
                WorkspaceMembership.objects.create(
                    workspace=workspace,
                    user=user,
                    role=role,
                )

                project = Project.objects.create(
                    workspace=workspace,
                    name="Preserved Project",
                    key=f"{role[:3].upper()}",
                )

                user_id = user.pk
                response = client.post(
                    reverse("account-deletion-confirm"),
                    {
                        "current_password": PASSWORD,
                        "confirmation": CONFIRMATION,
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )
                self.assertFalse(User.objects.filter(pk=user_id).exists())
                self.assertTrue(
                    Workspace.objects.filter(pk=workspace.pk).exists()
                )
                self.assertTrue(
                    Project.objects.filter(pk=project.pk).exists()
                )
                self.assertTrue(
                    WorkspaceMembership.objects.filter(
                        workspace=workspace,
                        user=owner,
                        role="owner",
                    ).exists()
                )
                self.assertFalse(
                    WorkspaceMembership.objects.filter(
                        workspace=workspace,
                        user_id=user_id,
                    ).exists()
                )

    def test_wrong_password_does_not_delete_account_or_workspace(self):
        workspace = self.create_workspace(
            "Protected Workspace", "protected-workspace", self.user, "owner"
        )

        response = self.confirm_deletion(password="WrongPassword!2026")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(Workspace.objects.filter(pk=workspace.pk).exists())

    def test_wrong_confirmation_phrase_does_not_delete_account_or_workspace(self):
        workspace = self.create_workspace(
            "Protected Workspace", "protected-workspace-phrase", self.user, "owner"
        )

        response = self.confirm_deletion(phrase="DELETE ACCOUNT")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(Workspace.objects.filter(pk=workspace.pk).exists())
