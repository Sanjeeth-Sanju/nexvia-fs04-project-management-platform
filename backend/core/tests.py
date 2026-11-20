from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from .models import (
    Workspace,
    WorkflowStatus,
    WorkspaceMembership,
    Project,
    ProjectMembership,
    Board,
    Sprint,
    Issue,
    IssueComment,
    IssueAttachment,
    AuditLog,
    WorkspaceInvitation,
    Subscription,
    StripeWebhookEvent,
    Notification,
)

User = get_user_model()


class WorkspaceListTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username="user_a",
            password="test-password-123",
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            password="test-password-123",
        )

        self.workspace_a = Workspace.objects.create(
            name="Company A",
            slug="company-a",
        )
        self.workspace_b = Workspace.objects.create(
            name="Company B",
            slug="company-b",
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace_a,
            user=self.user_a,
            role="owner",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace_b,
            user=self.user_b,
            role="owner",
        )

        self.project_a = Project.objects.create(
            workspace=self.workspace_a,
            name="Project A",
            key="PA",
            description="Company A project",
        )
        self.project_b = Project.objects.create(
            workspace=self.workspace_b,
            name="Project B",
            key="PB",
            description="Company B project",
        )

        self.board_a = Board.objects.create(
            project=self.project_a,
            name="Board A",
        )
        self.board_b = Board.objects.create(
            project=self.project_b,
            name="Board B",
        )

        self.sprint_a = Sprint.objects.create(
            project=self.project_a,
            name="Sprint A",
        )
        self.sprint_b = Sprint.objects.create(
            project=self.project_b,
            name="Sprint B",
        )

        self.issue_a = Issue.objects.create(
            project=self.project_a,
            board=self.board_a,
            title="Issue A",
        )
        self.issue_b = Issue.objects.create(
            project=self.project_b,
            board=self.board_b,
            title="Issue B",
        )

    def test_user_sees_only_their_workspaces(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/workspaces/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], "company-a")

    def test_unauthenticated_user_cannot_list_workspaces(self):
        response = self.client.get("/api/workspaces/")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_sees_only_their_projects(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/projects/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["key"], "PA")

    def test_user_sees_only_their_boards(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/boards/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Board A")

    def test_user_sees_only_their_sprints(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/sprints/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Sprint A")

    def test_user_sees_only_their_issues(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/issues/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Issue A")

    def test_issue_cannot_use_board_from_another_project(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            "/api/issues/",
            {
                "project": self.project_a.id,
                "board": self.board_b.id,
                "title": "Invalid cross-project issue",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("board", response.data)

    def test_issue_cannot_use_sprint_from_another_project(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            "/api/issues/",
            {
                "project": self.project_a.id,
                "board": self.board_a.id,
                "sprint": self.sprint_b.id,
                "title": "Invalid cross-project sprint",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("sprint", response.data)

    def test_issue_assignee_must_belong_to_workspace(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            "/api/issues/",
            {
                "project": self.project_a.id,
                "board": self.board_a.id,
                "assignee": self.user_b.id,
                "title": "Invalid external assignee",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("assignee", response.data)

    def test_user_can_retrieve_their_issue(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(
            f"/api/issues/{self.issue_a.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Issue A")

    def test_user_cannot_retrieve_another_workspace_issue(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(
            f"/api/issues/{self.issue_b.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_update_another_workspace_issue(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(
            f"/api/issues/{self.issue_b.id}/",
            {"title": "Unauthorized change"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.issue_b.refresh_from_db()
        self.assertEqual(self.issue_b.title, "Issue B")

    def test_user_cannot_delete_another_workspace_issue(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.delete(
            f"/api/issues/{self.issue_b.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            Issue.objects.filter(id=self.issue_b.id).exists()
        )

    def test_user_can_move_their_issue(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(
            f"/api/issues/{self.issue_a.id}/move/",
            {"status": "in_progress", "position": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.issue_a.refresh_from_db()
        self.assertEqual(self.issue_a.status, "in_progress")
        self.assertEqual(self.issue_a.position, 0)

    def test_user_cannot_move_another_workspace_issue(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(
            f"/api/issues/{self.issue_b.id}/move/",
            {"status": "done", "position": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.issue_b.refresh_from_db()
        self.assertEqual(self.issue_b.status, "todo")

    def test_move_rejects_invalid_status(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(
            f"/api/issues/{self.issue_a.id}/move/",
            {"status": "invalid_status", "position": 0},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_move_issue_reorders_same_lane(self):
        self.client.force_authenticate(user=self.user_a)

        issue_c = Issue.objects.create(
            project=self.project_a,
            board=self.board_a,
            title="Issue C",
            status="todo",
            position=2,
        )
        issue_d = Issue.objects.create(
            project=self.project_a,
            board=self.board_a,
            title="Issue D",
            status="todo",
            position=1,
        )

        self.issue_a.status = "todo"
        self.issue_a.position = 0
        self.issue_a.save()

        response = self.client.patch(
            f"/api/issues/{issue_c.id}/move/",
            {"status": "todo", "position": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        issues = list(
            Issue.objects.filter(
                board=self.board_a,
                status="todo",
            ).order_by("position", "id")
        )

        self.assertEqual(
            [issue.title for issue in issues],
            ["Issue A", "Issue C", "Issue D"],
        )
        self.assertEqual(
            [issue.position for issue in issues],
            [0, 1, 2],
        )

    def test_move_issue_between_lanes_reorders_both_lanes(self):
        self.client.force_authenticate(user=self.user_a)

        issue_c = Issue.objects.create(
            project=self.project_a,
            board=self.board_a,
            title="Issue C",
            status="in_progress",
            position=0,
        )

        issue_d = Issue.objects.create(
            project=self.project_a,
            board=self.board_a,
            title="Issue D",
            status="in_progress",
            position=1,
        )

        self.issue_a.status = "todo"
        self.issue_a.position = 0
        self.issue_a.save()

        response = self.client.patch(
            f"/api/issues/{self.issue_a.id}/move/",
            {"status": "in_progress", "position": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        todo_issues = list(
            Issue.objects.filter(
                board=self.board_a,
                status="todo",
            ).order_by("position", "id")
        )

        in_progress_issues = list(
            Issue.objects.filter(
                board=self.board_a,
                status="in_progress",
            ).order_by("position", "id")
        )

        self.assertEqual(
            [issue.title for issue in todo_issues],
            [],
        )
        self.assertEqual(
            [issue.title for issue in in_progress_issues],
            ["Issue C", "Issue A", "Issue D"],
        )
        self.assertEqual(
            [issue.position for issue in in_progress_issues],
            [0, 1, 2],
        )

    def test_move_rejects_missing_position(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(
            f"/api/issues/{self.issue_a.id}/move/",
            {"status": "in_progress"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.issue_a.refresh_from_db()
        self.assertEqual(self.issue_a.status, "todo")
        self.assertEqual(self.issue_a.position, 0)
    def test_user_can_list_issue_comments(self):
        self.client.force_authenticate(user=self.user_a)

        comment = IssueComment.objects.create(
            issue=self.issue_a,
            author=self.user_a,
            body="First comment",
        )

        response = self.client.get(
            f"/api/issues/{self.issue_a.id}/comments/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], comment.id)
        self.assertEqual(response.data[0]["body"], "First comment")

    def test_user_can_create_issue_comment(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            f"/api/issues/{self.issue_a.id}/comments/",
            {"body": "A new comment"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["body"], "A new comment")
        self.assertEqual(response.data["author"], str(self.user_a))

        comment = IssueComment.objects.get(id=response.data["id"])
        self.assertEqual(comment.issue, self.issue_a)
        self.assertEqual(comment.author, self.user_a)

    def test_user_cannot_access_comments_in_another_workspace(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(
            f"/api/issues/{self.issue_b.id}/comments/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    def test_user_can_upload_issue_attachment(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.user_a)

        uploaded_file = SimpleUploadedFile(
            "spec.txt",
            b"Attachment content",
            content_type="text/plain",
        )

        response = self.client.post(
            f"/api/issues/{self.issue_a.id}/attachments/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["filename"], "spec.txt")
        self.assertEqual(response.data["uploaded_by"], str(self.user_a))

    def test_user_can_list_issue_attachments(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.user_a)

        attachment_file = SimpleUploadedFile(
            "spec.txt",
            b"Attachment content",
            content_type="text/plain",
        )

        IssueAttachment.objects.create(
            issue=self.issue_a,
            uploaded_by=self.user_a,
            file=attachment_file,
            filename="spec.txt",
        )

        response = self.client.get(
            f"/api/issues/{self.issue_a.id}/attachments/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["filename"], "spec.txt")

    def test_user_cannot_access_attachments_in_another_workspace(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(
            f"/api/issues/{self.issue_b.id}/attachments/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    def test_user_can_list_workspace_audit_logs(self):
        self.client.force_authenticate(user=self.user_a)

        audit_log = AuditLog.objects.create(
            workspace=self.workspace_a,
            actor=self.user_a,
            action="issue.created",
            entity_type="Issue",
            entity_id=self.issue_a.id,
            details={"title": "Issue A"},
        )

        response = self.client.get(
            f"/api/workspaces/{self.workspace_a.id}/audit-logs/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], audit_log.id)
        self.assertEqual(response.data[0]["action"], "issue.created")

    def test_user_cannot_list_another_workspace_audit_logs(self):
        AuditLog.objects.create(
            workspace=self.workspace_b,
            actor=self.user_b,
            action="issue.created",
            entity_type="Issue",
            entity_id=self.issue_b.id,
            details={"title": "Issue B"},
        )

        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(
            f"/api/workspaces/{self.workspace_b.id}/audit-logs/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_unauthenticated_user_cannot_list_audit_logs(self):
        response = self.client.get(
            f"/api/workspaces/{self.workspace_a.id}/audit-logs/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_creating_issue_creates_audit_log(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            "/api/issues/",
            {
                "project": self.project_a.id,
                "board": self.board_a.id,
                "title": "Audit test issue",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        issue = Issue.objects.get(id=response.data["id"])

        audit_log = AuditLog.objects.get(
            workspace=self.workspace_a,
            entity_type="Issue",
            entity_id=issue.id,
            action="issue.created",
        )

        self.assertEqual(audit_log.actor, self.user_a)
        self.assertEqual(audit_log.details["title"], "Audit test issue")
        self.assertEqual(audit_log.details["project"], self.project_a.name)

    def test_moving_issue_creates_audit_log(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(
            f"/api/issues/{self.issue_a.id}/move/",
            {"status": "in_progress", "position": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        audit_log = AuditLog.objects.get(
            workspace=self.workspace_a,
            actor=self.user_a,
            action="issue.moved",
            entity_type="Issue",
            entity_id=self.issue_a.id,
        )

        self.assertEqual(audit_log.details["from_status"], "todo")
        self.assertEqual(audit_log.details["to_status"], "in_progress")
        self.assertEqual(audit_log.details["from_position"], 0)
        self.assertEqual(audit_log.details["to_position"], 0)  

    def test_creating_issue_comment_creates_audit_log(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            f"/api/issues/{self.issue_a.id}/comments/",
            {"body": "Audit log test comment"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        comment = IssueComment.objects.get(id=response.data["id"])

        audit_log = AuditLog.objects.get(
            workspace=self.workspace_a,
            actor=self.user_a,
            action="issue.comment.created",
            entity_type="IssueComment",
            entity_id=comment.id,
        )

        self.assertEqual(
            audit_log.details["issue_id"],
            self.issue_a.id,
        )
        self.assertEqual(
            audit_log.details["issue_title"],
            self.issue_a.title,
        )

    def test_issue_attachment_creation_creates_audit_log(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.user_a)

        uploaded_file = SimpleUploadedFile(
            "test-attachment.txt",
            b"Attachment test content",
            content_type="text/plain",
        )

        response = self.client.post(
            f"/api/issues/{self.issue_a.id}/attachments/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)

        attachment = IssueAttachment.objects.get(
            issue=self.issue_a,
            filename="test-attachment.txt",
        )

        audit_log = AuditLog.objects.get(
            action="issue.attachment.created",
            entity_type="IssueAttachment",
            entity_id=attachment.id,
        )

        self.assertEqual(audit_log.workspace, self.workspace_a)
        self.assertEqual(audit_log.actor, self.user_a)
        self.assertEqual(
            audit_log.details,
            {
                "issue_id": self.issue_a.id,
                "issue_title": self.issue_a.title,
                "filename": "test-attachment.txt",
            },
        )                                      
    def test_deleting_issue_attachment_creates_audit_log(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.user_a)

        attachment = IssueAttachment.objects.create(
            issue=self.issue_a,
            uploaded_by=self.user_a,
            file=SimpleUploadedFile(
                "delete-me.txt",
                b"Attachment content",
                content_type="text/plain",
            ),
            filename="delete-me.txt",
        )

        response = self.client.delete(
            f"/api/attachments/{attachment.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(
            IssueAttachment.objects.filter(id=attachment.id).exists()
        )

        audit_log = AuditLog.objects.get(
            action="issue.attachment.deleted",
            entity_type="IssueAttachment",
            entity_id=attachment.id,
        )

        self.assertEqual(audit_log.workspace, self.workspace_a)
        self.assertEqual(audit_log.actor, self.user_a)
        self.assertEqual(
            audit_log.details,
            {
                "issue_id": self.issue_a.id,
                "issue_title": self.issue_a.title,
                "filename": "delete-me.txt",
            },
        )        
    def test_user_cannot_delete_another_workspace_attachment(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.user_a)

        attachment = IssueAttachment.objects.create(
            issue=self.issue_b,
            uploaded_by=self.user_b,
            file=SimpleUploadedFile(
                "private.txt",
                b"Private attachment",
                content_type="text/plain",
            ),
            filename="private.txt",
        )

        response = self.client.delete(
            f"/api/attachments/{attachment.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertTrue(
            IssueAttachment.objects.filter(id=attachment.id).exists()
        )

        self.assertFalse(
            AuditLog.objects.filter(
                action="issue.attachment.deleted",
                entity_id=attachment.id,
            ).exists()
        )
    def test_new_workspace_gets_default_workflow_statuses(self):
        workspace = Workspace.objects.create(
            name="Workflow Test",
            slug="workflow-test",
        )

        statuses = WorkflowStatus.objects.filter(
            workspace=workspace
        ).order_by("position")

        self.assertEqual(statuses.count(), 3)
        self.assertEqual(
            list(statuses.values_list("slug", flat=True)),
            ["todo", "in_progress", "done"],
        )
        self.assertTrue(statuses.get(slug="todo").is_default)
        self.assertTrue(statuses.get(slug="done").is_completed)

    def test_move_accepts_custom_workspace_status(self):
        self.client.force_authenticate(user=self.user_a)

        custom_status = WorkflowStatus.objects.create(
            workspace=self.project_a.workspace,
            name="In Review",
            slug="in_review",
            position=3,
        )

        response = self.client.patch(
            f"/api/issues/{self.issue_a.id}/move/",
            {"status": custom_status.slug, "position": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.issue_a.refresh_from_db()
        self.assertEqual(self.issue_a.status, "in_review")

class WorkspaceRolePermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="role_owner",
            password="test-password-123",
        )
        self.admin = User.objects.create_user(
            username="role_admin",
            password="test-password-123",
        )
        self.member = User.objects.create_user(
            username="role_member",
            password="test-password-123",
        )

        self.workspace = Workspace.objects.create(
            name="Role Test Workspace",
            slug="role-test-workspace",
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role="owner",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.admin,
            role="admin",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role="member",
        )

        self.project = Project.objects.create(
            workspace=self.workspace,
            name="Role Test Project",
            key="RTP",
        )
        ProjectMembership.objects.create(
            project=self.project,
            user=self.member,
        )
        self.board = Board.objects.create(
            project=self.project,
            name="Role Test Board",
        )        

    def test_owner_can_update_member_project_assignments(self):
        second_project = Project.objects.create(
            workspace=self.workspace,
            name="Second Project",
            key="RTP2",
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(
            f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/projects/",
            {"project_ids": [second_project.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["project_ids"], [second_project.id])
        self.assertSetEqual(
            set(ProjectMembership.objects.filter(
                user=self.member,
                project__workspace=self.workspace,
            ).values_list("project_id", flat=True)),
            {second_project.id},
        )

    def test_admin_can_update_member_project_assignments(self):
        second_project = Project.objects.create(
            workspace=self.workspace,
            name="Admin Assigned Project",
            key="AAP",
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.put(
            f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/projects/",
            {"project_ids": [second_project.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["project_ids"], [second_project.id])

    def test_regular_member_cannot_update_project_assignments(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.put(
            f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/projects/",
            {"project_ids": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            ProjectMembership.objects.filter(
                project=self.project,
                user=self.member,
            ).exists()
        )

    def test_assignment_rejects_project_from_another_workspace(self):
        other_workspace = Workspace.objects.create(
            name="Other Assignment Workspace",
            slug="other-assignment-workspace",
        )
        foreign_project = Project.objects.create(
            workspace=other_workspace,
            name="Foreign Project",
            key="FP",
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(
            f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/projects/",
            {"project_ids": [foreign_project.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            ProjectMembership.objects.filter(
                project=self.project,
                user=self.member,
            ).exists()
        )

    def test_assignment_changes_only_apply_to_workspace_members_with_member_role(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(
            f"/api/workspaces/{self.workspace.id}/members/{self.owner.id}/projects/",
            {"project_ids": [self.project.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_removing_project_access_preserves_existing_issues(self):
        existing_issue = Issue.objects.create(
            project=self.project,
            board=self.board,
            title="Existing issue survives access removal",
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(
            f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/projects/",
            {"project_ids": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            ProjectMembership.objects.filter(
                project=self.project,
                user=self.member,
            ).exists()
        )
        self.assertTrue(Issue.objects.filter(pk=existing_issue.pk).exists())

    def test_owner_can_delete_project_permanently(self):
        project_id = self.project.id
        board_id = self.board.id
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f"/api/projects/{project_id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(id=project_id).exists())
        self.assertFalse(Board.objects.filter(id=board_id).exists())

    def test_admin_cannot_delete_project(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(f"/api/projects/{self.project.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Project.objects.filter(id=self.project.id).exists())

    def test_member_cannot_delete_project(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.delete(f"/api/projects/{self.project.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Project.objects.filter(id=self.project.id).exists())

    def test_owner_can_create_project(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/projects/",
            {
                "workspace": self.workspace.id,
                "name": "Owner Project",
                "key": "OWN",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_can_create_project(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/projects/",
            {
                "workspace": self.workspace.id,
                "name": "Admin Project",
                "key": "ADM",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_member_cannot_create_project(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            "/api/projects/",
            {
                "workspace": self.workspace.id,
                "name": "Member Project",
                "key": "MEM",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_create_board(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            "/api/boards/",
            {
                "project": self.project.id,
                "name": "Member Board",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_create_sprint(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            "/api/sprints/",
            {
                "project": self.project.id,
                "name": "Member Sprint",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_list_projects(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.get("/api/projects/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_member_can_create_issue(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            "/api/issues/",
            {
                "project": self.project.id,
                "board": self.board.id,
                "title": "Member-created issue",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["title"],
            "Member-created issue",
        )

    def test_member_cannot_update_issue(self):
        issue = Issue.objects.create(
            project=self.project,
            board=self.board,
            title="Original issue",
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"/api/issues/{issue.id}/",
            {"title": "Updated by member"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        issue.refresh_from_db()
        self.assertEqual(issue.title, "Original issue")

    def test_member_cannot_delete_issue(self):
        issue = Issue.objects.create(
            project=self.project,
            board=self.board,
            title="Issue protected from member deletion",
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.delete(f"/api/issues/{issue.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Issue.objects.filter(pk=issue.pk).exists())

    def test_member_cannot_complete_issue(self):
        from core.models import WorkflowStatus

        WorkflowStatus.objects.get_or_create(
            workspace=self.workspace,
            slug="done",
            defaults={"name": "Done", "position": 2, "is_completed": True},
        )
        issue = Issue.objects.create(
            project=self.project, board=self.board, title="Member completion test"
        )
        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"/api/issues/{issue.id}/move/",
            {"status": "done", "position": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        issue.refresh_from_db()
        self.assertEqual(issue.status, "todo")

    def test_member_cannot_reopen_completed_issue(self):
        from core.models import WorkflowStatus

        WorkflowStatus.objects.get_or_create(
            workspace=self.workspace,
            slug="done",
            defaults={"name": "Done", "position": 2, "is_completed": True},
        )
        issue = Issue.objects.create(
            project=self.project, board=self.board, title="Member reopen test",
            status="done",
        )
        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"/api/issues/{issue.id}/move/",
            {"status": "todo", "position": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        issue.refresh_from_db()
        self.assertEqual(issue.status, "done")

    def test_owner_can_complete_and_reopen_issue(self):
        from core.models import WorkflowStatus

        WorkflowStatus.objects.get_or_create(
            workspace=self.workspace,
            slug="done",
            defaults={"name": "Done", "position": 2, "is_completed": True},
        )
        issue = Issue.objects.create(
            project=self.project, board=self.board, title="Owner workflow test"
        )
        self.client.force_authenticate(user=self.owner)

        complete_response = self.client.patch(
            f"/api/issues/{issue.id}/move/",
            {"status": "done", "position": 0},
            format="json",
        )
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)

        reopen_response = self.client.patch(
            f"/api/issues/{issue.id}/move/",
            {"status": "todo", "position": 0},
            format="json",
        )
        self.assertEqual(reopen_response.status_code, status.HTTP_200_OK)

        issue.refresh_from_db()
        self.assertEqual(issue.status, "todo")

    def test_admin_can_complete_and_reopen_issue(self):
        from core.models import WorkflowStatus

        WorkflowStatus.objects.get_or_create(
            workspace=self.workspace,
            slug="done",
            defaults={"name": "Done", "position": 2, "is_completed": True},
        )
        issue = Issue.objects.create(
            project=self.project, board=self.board, title="Admin workflow test"
        )
        self.client.force_authenticate(user=self.admin)

        complete_response = self.client.patch(
            f"/api/issues/{issue.id}/move/",
            {"status": "done", "position": 0},
            format="json",
        )
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)

        reopen_response = self.client.patch(
            f"/api/issues/{issue.id}/move/",
            {"status": "todo", "position": 0},
            format="json",
        )
        self.assertEqual(reopen_response.status_code, status.HTTP_200_OK)

        issue.refresh_from_db()
        self.assertEqual(issue.status, "todo")

    def test_member_can_move_issue(self):
        issue = Issue.objects.create(
            project=self.project,
            board=self.board,
            title="Issue to move",
            status="todo",
            position=0,
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"/api/issues/{issue.id}/move/",
            {
                "status": "in_progress",
                "position": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        issue.refresh_from_db()
        self.assertEqual(issue.status, "in_progress")
        self.assertEqual(issue.position, 0)    
        

    def test_member_cannot_create_issue_in_unassigned_project(self):
        unassigned_project = Project.objects.create(
            workspace=self.workspace,
            name="Unassigned Project",
            key="UNAS",
        )
        unassigned_board = Board.objects.create(
            project=unassigned_project,
            name="Unassigned Board",
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            "/api/issues/",
            {
                "project": unassigned_project.id,
                "board": unassigned_board.id,
                "title": "Unauthorized issue",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Issue.objects.filter(
                project=unassigned_project,
                title="Unauthorized issue",
            ).exists()
        )

    def test_member_cannot_move_issue_to_unassigned_project(self):
        issue = Issue.objects.create(
            project=self.project,
            board=self.board,
            title="Assigned project issue",
        )
        unassigned_project = Project.objects.create(
            workspace=self.workspace,
            name="Unassigned Move Target",
            key="UMT",
        )
        unassigned_board = Board.objects.create(
            project=unassigned_project,
            name="Unassigned Move Board",
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.patch(
            f"/api/issues/{issue.id}/",
            {
                "project": unassigned_project.id,
                "board": unassigned_board.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        issue.refresh_from_db()
        self.assertEqual(issue.project_id, self.project.id)
        self.assertEqual(issue.board_id, self.board.id)

    def test_owner_can_create_issue(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/issues/",
            {
                "project": self.project.id,
                "board": self.board.id,
                "title": "Owner-created issue",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_can_create_issue(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/issues/",
            {
                "project": self.project.id,
                "board": self.board.id,
                "title": "Admin-created issue",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_member_sees_audit_logs_only_for_assigned_projects(self):
        second_project = Project.objects.create(
            workspace=self.workspace,
            name="Unassigned Project",
            key="UNASSIGNED",
        )
        second_board = Board.objects.create(
            project=second_project,
            name="Unassigned Board",
        )
        second_issue = Issue.objects.create(
            project=second_project,
            board=second_board,
            title="Private Issue",
        )

        assigned_issue = Issue.objects.create(
            project=self.project,
            board=self.board,
            title="Assigned Issue",
        )

        visible_log = AuditLog.objects.create(
            workspace=self.workspace,
            actor=self.owner,
            action="issue.created",
            entity_type="Issue",
            entity_id=assigned_issue.id,
            details={"title": assigned_issue.title},
        )

        AuditLog.objects.create(
            workspace=self.workspace,
            actor=self.owner,
            action="issue.created",
            entity_type="Issue",
            entity_id=second_issue.id,
            details={"title": second_issue.title},
        )

        AuditLog.objects.create(
            workspace=self.workspace,
            actor=self.owner,
            action="issue.comment.created",
            entity_type="IssueComment",
            entity_id=9991,
            details={"issue_id": second_issue.id},
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.get(
            f"/api/workspaces/{self.workspace.id}/audit-logs/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertEqual(returned_ids, {visible_log.id})

    def test_owner_can_see_all_workspace_audit_logs(self):
        second_project = Project.objects.create(
            workspace=self.workspace,
            name="Owner Visibility Project",
            key="OWNVIS",
        )
        second_board = Board.objects.create(
            project=second_project,
            name="Owner Visibility Board",
        )
        second_issue = Issue.objects.create(
            project=second_project,
            board=second_board,
            title="Owner Visibility Issue",
        )

        first_log = AuditLog.objects.create(
            workspace=self.workspace,
            actor=self.owner,
            action="issue.created",
            entity_type="Issue",
            entity_id=second_issue.id,
            details={},
        )
        second_log = AuditLog.objects.create(
            workspace=self.workspace,
            actor=self.owner,
            action="issue.comment.created",
            entity_type="IssueComment",
            entity_id=9992,
            details={"issue_id": second_issue.id},
        )

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(
            f"/api/workspaces/{self.workspace.id}/audit-logs/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertTrue({first_log.id, second_log.id}.issubset(returned_ids))

    def test_admin_can_see_all_workspace_audit_logs(self):
        second_project = Project.objects.create(
            workspace=self.workspace,
            name="Admin Visibility Project",
            key="ADMVIS",
        )
        second_board = Board.objects.create(
            project=second_project,
            name="Admin Visibility Board",
        )
        second_issue = Issue.objects.create(
            project=second_project,
            board=second_board,
            title="Admin Visibility Issue",
        )

        audit_log = AuditLog.objects.create(
            workspace=self.workspace,
            actor=self.owner,
            action="issue.created",
            entity_type="Issue",
            entity_id=second_issue.id,
            details={},
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            f"/api/workspaces/{self.workspace.id}/audit-logs/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertIn(audit_log.id, returned_ids)


class WorkflowStatusAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="workflow_owner",
            password="test-password-123",
        )
        self.member = User.objects.create_user(
            username="workflow_member",
            password="test-password-123",
        )
        self.outsider = User.objects.create_user(
            username="workflow_outsider",
            password="test-password-123",
        )

        self.workspace = Workspace.objects.create(
            name="Workflow Test Workspace",
            slug="workflow-test-workspace",
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role="owner",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role="member",
        )

        self.url = (
            f"/api/workspaces/{self.workspace.id}/workflow-statuses/"
        )

    def test_workspace_member_can_list_workflow_statuses(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(
            [item["slug"] for item in response.data],
            ["todo", "in_progress", "done"],
        )


    def test_owner_cannot_create_custom_workflow_status(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                "name": "In Review",
                "slug": "in_review",
                "position": 3,
                "is_completed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(
            WorkflowStatus.objects.filter(
                workspace=self.workspace,
                slug="in_review",
            ).exists()
        )

    def test_member_cannot_create_workflow_status(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            self.url,
            {
                "name": "In Review",
                "slug": "in_review",
                "position": 3,
                "is_completed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(
            WorkflowStatus.objects.filter(
                workspace=self.workspace,
                slug="in_review",
            ).exists()
        )
    def test_non_member_cannot_access_workflow_statuses(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_custom_workflow_creation_is_disabled_without_audit_log(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                "name": "In Review",
                "slug": "in_review",
                "position": 3,
                "is_completed": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(
            AuditLog.objects.filter(
                workspace=self.workspace,
                actor=self.owner,
                action="workflow_status.created",
            ).exists()
        )
class WorkspaceCreationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="workspace_creator",
            password="test-password-123",
        )

    def test_authenticated_user_can_create_workspace(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/workspaces/",
            {"name": "Acme Technologies"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Acme Technologies")
        self.assertEqual(response.data["slug"], "acme-technologies")

        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace__slug="acme-technologies",
                user=self.user,
                role="owner",
            ).exists()
        )

    def test_workspace_creator_automatically_becomes_owner(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/workspaces/",
            {"name": "Owner Test Company"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        workspace = Workspace.objects.get(
            slug="owner-test-company"
        )

        membership = WorkspaceMembership.objects.get(
            workspace=workspace,
            user=self.user,
        )

        self.assertEqual(membership.role, "owner")

    def test_workspace_creation_generates_default_statuses(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/workspaces/",
            {"name": "Workflow Company"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        workspace = Workspace.objects.get(
            slug="workflow-company"
        )

        statuses = WorkflowStatus.objects.filter(
            workspace=workspace
        ).order_by("position")

        self.assertEqual(statuses.count(), 3)

        self.assertEqual(
            list(statuses.values_list("slug", flat=True)),
            ["todo", "in_progress", "done"],
        )

    def test_duplicate_workspace_name_gets_unique_slug(self):
        Workspace.objects.create(
            name="Acme",
            slug="acme",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/workspaces/",
            {"name": "Acme"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["slug"], "acme-2")

    def test_unauthenticated_user_cannot_create_workspace(self):
        response = self.client.post(
            "/api/workspaces/",
            {"name": "Unauthorized Company"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertFalse(
            Workspace.objects.filter(
                name="Unauthorized Company"
            ).exists()
        )


class WorkspaceInvitationSecurityTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="inv_owner", email="inv_owner@example.com",
            password="test-password-123",
        )
        self.admin = User.objects.create_user(
            username="inv_admin", email="inv_admin@example.com",
            password="test-password-123",
        )
        self.member = User.objects.create_user(
            username="inv_member", email="inv_member@example.com",
            password="test-password-123",
        )
        self.invitee = User.objects.create_user(
            username="inv_invitee", email="invitee@example.com",
            password="test-password-123",
        )
        self.outsider = User.objects.create_user(
            username="inv_outsider", email="outsider@example.com",
            password="test-password-123",
        )

        self.workspace = Workspace.objects.create(
            name="Invitation Workspace", slug="invitation-workspace",
        )
        for user, role in [
            (self.owner, "owner"),
            (self.admin, "admin"),
            (self.member, "member"),
        ]:
            WorkspaceMembership.objects.create(
                workspace=self.workspace, user=user, role=role,
            )

        self.project = Project.objects.create(
            workspace=self.workspace, name="Invitation Project", key="INVP",
        )
        self.foreign_workspace = Workspace.objects.create(
            name="Foreign Workspace", slug="foreign-invitation-workspace",
        )
        self.foreign_project = Project.objects.create(
            workspace=self.foreign_workspace,
            name="Foreign Project", key="FPRJ",
        )
        self.url = f"/api/workspaces/{self.workspace.id}/invitations/"

    def make_invitation(self, **kwargs):
        values = {
            "workspace": self.workspace,
            "email": "invitee@example.com",
            "role": "member",
            "invited_by": self.owner,
        }
        values.update(kwargs)
        return WorkspaceInvitation.objects.create(**values)

    def test_owner_can_invite_member_to_workspace_project(self):
        self.client.force_authenticate(user=self.owner)
        with patch("core.email_service.send_workspace_invitation_email"):
            response = self.client.post(
                self.url,
                {
                    "email": " NEWUSER@example.com ",
                    "role": "member",
                    "project_ids": [self.project.id],
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invitation = WorkspaceInvitation.objects.get(id=response.data["id"])
        self.assertEqual(invitation.email, "newuser@example.com")
        self.assertQuerySetEqual(
            invitation.projects.order_by("id"),
            [self.project],
        )

    def test_member_cannot_create_invitation(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            self.url,
            {
                "email": "newuser@example.com",
                "role": "member",
                "project_ids": [self.project.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_invitation_requires_project_assignment(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.url,
            {
                "email": "newuser@example.com",
                "role": "member",
                "project_ids": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_invitation_rejects_invalid_project_id_types(self):
        self.client.force_authenticate(user=self.owner)
        for invalid_id in [True, 1.5, "invalid", 0, -1]:
            with self.subTest(project_id=invalid_id):
                response = self.client.post(
                    self.url,
                    {
                        "email": f"bad{str(invalid_id).replace('.', '')}@example.com",
                        "role": "member",
                        "project_ids": [invalid_id],
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invitation_rejects_foreign_workspace_project(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.url,
            {
                "email": "foreign@example.com",
                "role": "member",
                "project_ids": [self.foreign_project.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_pending_invitation_is_rejected(self):
        self.make_invitation()
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.url,
            {
                "email": "INVITEE@example.com",
                "role": "member",
                "project_ids": [self.project.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_acceptance_requires_matching_email(self):
        invitation = self.make_invitation()
        self.client.force_authenticate(user=self.outsider)
        response = self.client.post(
            f"/api/invitations/{invitation.token}/accept/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "pending")

    def test_invitee_acceptance_assigns_only_invited_project(self):
        invitation = self.make_invitation()
        invitation.projects.add(self.project)
        self.client.force_authenticate(user=self.invitee)
        response = self.client.post(
            f"/api/invitations/{invitation.token}/accept/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["project_ids"], [self.project.id])
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "accepted")
        self.assertIsNotNone(invitation.accepted_at)

    def test_expired_invitation_cannot_be_accepted(self):
        invitation = self.make_invitation(
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.client.force_authenticate(user=self.invitee)
        response = self.client.post(
            f"/api/invitations/{invitation.token}/accept/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "expired")

    def test_member_cannot_revoke_invitation(self):
        invitation = self.make_invitation()
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            f"/api/invitations/{invitation.id}/revoke/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "pending")

    def test_revoked_invitation_cannot_be_accepted(self):
        invitation = self.make_invitation(status="revoked")
        self.client.force_authenticate(user=self.invitee)
        response = self.client.post(
            f"/api/invitations/{invitation.token}/accept/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                workspace=self.workspace, user=self.invitee,
            ).exists()
        )


class SameWorkspaceCrossProjectSecurityTests(APITestCase):
    """
    A workspace member assigned to Project A must not access Project B,
    even when both projects belong to the same workspace.
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            username="cross_project_owner",
            password="test-password-123",
        )
        self.member = User.objects.create_user(
            username="cross_project_member",
            password="test-password-123",
        )

        self.workspace = Workspace.objects.create(
            name="Cross Project Workspace",
            slug="cross-project-workspace",
        )

        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role="owner",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role="member",
        )

        self.project_a = Project.objects.create(
            workspace=self.workspace,
            name="Project A",
            key="CPA",
        )
        self.project_b = Project.objects.create(
            workspace=self.workspace,
            name="Project B",
            key="CPB",
        )

        ProjectMembership.objects.create(
            project=self.project_a,
            user=self.member,
        )

        self.board_a = Board.objects.create(
            project=self.project_a,
            name="Project A Board",
        )
        self.board_b = Board.objects.create(
            project=self.project_b,
            name="Project B Board",
        )

        self.issue_a = Issue.objects.create(
            project=self.project_a,
            board=self.board_a,
            title="Issue in assigned project",
        )
        self.issue_b = Issue.objects.create(
            project=self.project_b,
            board=self.board_b,
            title="Issue in unassigned project",
        )

        self.client.force_authenticate(user=self.member)

    def test_member_can_retrieve_issue_in_assigned_project(self):
        response = self.client.get(
            f"/api/issues/{self.issue_a.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_member_cannot_retrieve_issue_in_other_project(self):
        response = self.client.get(
            f"/api/issues/{self.issue_b.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_member_cannot_update_issue_in_other_project(self):
        response = self.client.patch(
            f"/api/issues/{self.issue_b.id}/",
            {"title": "Unauthorized change"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.issue_b.refresh_from_db()
        self.assertEqual(
            self.issue_b.title,
            "Issue in unassigned project",
        )

    def test_member_cannot_delete_issue_in_other_project(self):
        response = self.client.delete(
            f"/api/issues/{self.issue_b.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Issue.objects.filter(pk=self.issue_b.pk).exists())

    def test_member_cannot_move_issue_in_other_project(self):
        response = self.client.patch(
            f"/api/issues/{self.issue_b.id}/move/",
            {"status": "in_progress", "position": 0},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.issue_b.refresh_from_db()
        self.assertEqual(self.issue_b.status, "todo")

    def test_member_cannot_list_comments_on_other_project_issue(self):
        response = self.client.get(
            f"/api/issues/{self.issue_b.id}/comments/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_member_cannot_create_comment_on_other_project_issue(self):
        response = self.client.post(
            f"/api/issues/{self.issue_b.id}/comments/",
            {"body": "Unauthorized comment"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            IssueComment.objects.filter(issue=self.issue_b).exists()
        )

    def test_member_cannot_list_attachments_on_other_project_issue(self):
        response = self.client.get(
            f"/api/issues/{self.issue_b.id}/attachments/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_member_cannot_upload_attachment_to_other_project_issue(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded_file = SimpleUploadedFile(
            "unauthorized.txt",
            b"should not be uploaded",
            content_type="text/plain",
        )

        response = self.client.post(
            f"/api/issues/{self.issue_b.id}/attachments/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            IssueAttachment.objects.filter(issue=self.issue_b).exists()
        )

    def test_member_cannot_delete_attachment_on_other_project_issue(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        attachment = IssueAttachment.objects.create(
            issue=self.issue_b,
            uploaded_by=self.owner,
            file=SimpleUploadedFile(
                "protected.txt",
                b"protected attachment",
                content_type="text/plain",
            ),
            filename="protected.txt",
        )

        response = self.client.delete(
            f"/api/attachments/{attachment.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            IssueAttachment.objects.filter(pk=attachment.pk).exists()
        )


class StripeWebhookReliabilityTests(APITestCase):
    webhook_url = "/api/billing/webhook/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="stripe_test_user",
            email="stripe-test@example.com",
            password="test-password-123",
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            plan="free",
            status="active",
            stripe_customer_id="cus_test_123",
        )

        self.subscription_object = {
            "id": "sub_test_123",
            "customer": "cus_test_123",
            "status": "active",
            "metadata": {"user_id": str(self.user.pk), "plan": "pro"},
            "items": {
                "data": [{"price": {"id": "price_pro_test"}}],
            },
            "current_period_start": 1790000000,
            "current_period_end": 1792592000,
            "cancel_at_period_end": False,
        }

    def make_event(self, event_id, created, subscription_object=None):
        return {
            "id": event_id,
            "type": "customer.subscription.updated",
            "created": created,
            "data": {
                "object": subscription_object or self.subscription_object,
            },
        }

    def post_event(self, event):
        return self.client.post(
            self.webhook_url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test-signature",
        )

    def test_subscription_webhook_updates_plan(self):
        event = self.make_event("evt_subscription_update_1", 1790000100)

        with self.settings(
            STRIPE_WEBHOOK_SECRET="whsec_test",
            STRIPE_SECRET_KEY="sk_test",
            STRIPE_PRICE_PRO="price_pro_test",
            STRIPE_PRICE_BUSINESS="price_business_test",
        ):
            with patch(
                "core.billing_views.stripe.Webhook.construct_event",
                return_value=event,
            ):
                response = self.post_event(event)

        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan, "pro")
        self.assertEqual(self.subscription.status, "active")
        self.assertEqual(self.subscription.last_stripe_event_created, 1790000100)
        self.assertTrue(
            StripeWebhookEvent.objects.filter(
                stripe_event_id="evt_subscription_update_1"
            ).exists()
        )

    def test_duplicate_webhook_event_is_processed_only_once(self):
        first_event = self.make_event("evt_duplicate_1", 1790000100)

        changed_object = {
            **self.subscription_object,
            "status": "canceled",
        }
        second_delivery = self.make_event(
            "evt_duplicate_1",
            1790000200,
            changed_object,
        )

        with self.settings(
            STRIPE_WEBHOOK_SECRET="whsec_test",
            STRIPE_SECRET_KEY="sk_test",
            STRIPE_PRICE_PRO="price_pro_test",
            STRIPE_PRICE_BUSINESS="price_business_test",
        ):
            with patch(
                "core.billing_views.stripe.Webhook.construct_event",
                side_effect=[first_event, second_delivery],
            ):
                first_response = self.post_event(first_event)
                second_response = self.post_event(second_delivery)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "active")
        self.assertEqual(
            StripeWebhookEvent.objects.filter(
                stripe_event_id="evt_duplicate_1"
            ).count(),
            1,
        )

    def test_older_webhook_event_cannot_overwrite_newer_state(self):
        self.subscription.plan = "business"
        self.subscription.status = "active"
        self.subscription.last_stripe_event_created = 1790000200
        self.subscription.save()

        older_object = {
            **self.subscription_object,
            "status": "canceled",
            "items": {
                "data": [{"price": {"id": "price_pro_test"}}],
            },
        }
        event = self.make_event(
            "evt_stale_1",
            1790000100,
            older_object,
        )

        with self.settings(
            STRIPE_WEBHOOK_SECRET="whsec_test",
            STRIPE_SECRET_KEY="sk_test",
            STRIPE_PRICE_PRO="price_pro_test",
            STRIPE_PRICE_BUSINESS="price_business_test",
        ):
            with patch(
                "core.billing_views.stripe.Webhook.construct_event",
                return_value=event,
            ):
                response = self.post_event(event)

        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan, "business")
        self.assertEqual(self.subscription.status, "active")
        self.assertEqual(self.subscription.last_stripe_event_created, 1790000200)

    def test_invalid_webhook_signature_is_rejected(self):
        with self.settings(STRIPE_WEBHOOK_SECRET="whsec_test"):
            with patch(
                "core.billing_views.stripe.Webhook.construct_event",
                side_effect=ValueError("Invalid payload"),
            ):
                response = self.post_event({})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(StripeWebhookEvent.objects.count(), 0)



class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username="notification_user_a",
            password="test-password-123",
        )
        self.user_b = User.objects.create_user(
            username="notification_user_b",
            password="test-password-123",
        )

        self.notification_a = Notification.objects.create(
            recipient=self.user_a,
            event_type="system",
            title="Welcome",
            message="Your account is ready.",
        )
        self.notification_b = Notification.objects.create(
            recipient=self.user_b,
            event_type="system",
            title="Other user's notification",
            message="This belongs to another user.",
        )

    def test_user_only_sees_their_notifications(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/notifications/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            self.notification_a.id,
        )
        self.assertEqual(response.data["unread_count"], 1)

    def test_unread_filter_returns_only_unread_notifications(self):
        Notification.objects.create(
            recipient=self.user_a,
            event_type="system",
            title="Already read",
            message="This notification has been read.",
            is_read=True,
            read_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/notifications/?unread=true")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertFalse(response.data["results"][0]["is_read"])
        self.assertEqual(response.data["unread_count"], 1)

    def test_user_can_mark_their_notification_as_read(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(
            f"/api/notifications/{self.notification_a.id}/read/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification_a.refresh_from_db()
        self.assertTrue(self.notification_a.is_read)
        self.assertIsNotNone(self.notification_a.read_at)

    def test_user_can_mark_all_their_notifications_as_read(self):
        Notification.objects.create(
            recipient=self.user_a,
            event_type="system",
            title="Second notification",
            message="Another notification.",
        )
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post("/api/notifications/read-all/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"], 2)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.user_a,
                is_read=False,
            ).exists()
        )
        self.assertFalse(self.notification_b.is_read)

    def test_user_can_delete_their_notification(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.delete(
            f"/api/notifications/{self.notification_a.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Notification.objects.filter(pk=self.notification_a.id).exists()
        )

    def test_user_cannot_delete_another_users_notification(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.delete(
            f"/api/notifications/{self.notification_b.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            Notification.objects.filter(pk=self.notification_b.id).exists()
        )

    def test_clear_all_deletes_only_the_authenticated_users_notifications(self):
        Notification.objects.create(
            recipient=self.user_a,
            event_type="system",
            title="Another notification",
            message="Another notification for user A.",
        )
        self.client.force_authenticate(user=self.user_a)

        response = self.client.delete("/api/notifications/clear-all/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["deleted"], 2)
        self.assertFalse(
            Notification.objects.filter(recipient=self.user_a).exists()
        )
        self.assertTrue(
            Notification.objects.filter(recipient=self.user_b).exists()
        )

    def test_unauthenticated_user_cannot_list_notifications(self):
        response = self.client.get("/api/notifications/")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )



class NotificationEventTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="event_owner",
            password="test-password-123",
        )
        self.member = User.objects.create_user(
            username="event_member",
            password="test-password-123",
        )

        self.workspace = Workspace.objects.create(
            name="Notification Event Workspace",
            slug="notification-event-workspace",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role="owner",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role="member",
        )

        self.project = Project.objects.create(
            workspace=self.workspace,
            name="Notification Event Project",
            key="NEP",
        )
        ProjectMembership.objects.create(
            project=self.project,
            user=self.member,
        )
        self.board = Board.objects.create(
            project=self.project,
            name="Notification Event Board",
        )
        self.issue = Issue.objects.create(
            project=self.project,
            board=self.board,
            title="Notification test issue",
        )

    def test_assigning_issue_notifies_new_assignee(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/api/issues/{self.issue.id}/",
            {"assignee": self.member.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(
            recipient=self.member,
            event_type="issue_assigned",
        )
        self.assertEqual(notification.actor, self.owner)
        self.assertEqual(notification.project, self.project)
        self.assertIn(self.issue.title, notification.message)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.owner,
                event_type="issue_assigned",
            ).exists()
        )

    def test_comment_notifies_assignee_but_not_commenter(self):
        self.issue.assignee = self.member
        self.issue.save(update_fields=["assignee"])
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f"/api/issues/{self.issue.id}/comments/",
            {"body": "A notification test comment"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get(
            recipient=self.member,
            event_type="issue_commented",
        )
        self.assertEqual(notification.actor, self.owner)
        self.assertEqual(
            notification.metadata["issue_id"],
            self.issue.id,
        )
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.owner,
                event_type="issue_commented",
            ).exists()
        )

    def test_role_change_notifies_affected_member(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/role/",
            {"role": "admin"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(
            recipient=self.member,
            event_type="member_role_changed",
        )
        self.assertEqual(notification.actor, self.owner)
        self.assertEqual(notification.workspace, self.workspace)
        self.assertEqual(notification.metadata["old_role"], "member")
        self.assertEqual(notification.metadata["new_role"], "admin")

    def test_member_removal_notification_survives_membership_deletion(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(
            f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                workspace=self.workspace,
                user=self.member,
            ).exists()
        )

        notification = Notification.objects.get(
            recipient=self.member,
            event_type="workspace_removed",
        )
        self.assertEqual(notification.actor, self.owner)
        self.assertEqual(notification.workspace, self.workspace)

        self.client.force_authenticate(user=self.member)
        inbox_response = self.client.get("/api/notifications/")

        self.assertEqual(inbox_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(inbox_response.data["results"]), 1)
        self.assertEqual(
            inbox_response.data["results"][0]["id"],
            notification.id,
        )
