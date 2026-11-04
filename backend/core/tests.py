from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import (
    Workspace,
    WorkflowStatus,
    WorkspaceMembership,
    Project,
    Board,
    Sprint,
    Issue,
    IssueComment,
    IssueAttachment,
    AuditLog,
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
        self.board = Board.objects.create(
            project=self.project,
            name="Role Test Board",
        )        

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

    def test_member_can_update_issue(self):
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        issue.refresh_from_db()
        self.assertEqual(issue.title, "Updated by member")        

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

    def test_owner_can_create_custom_workflow_status(self):
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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "In Review")
        self.assertEqual(response.data["workspace"], self.workspace.id)

        self.assertTrue(
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

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
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

    def test_creating_workflow_status_creates_audit_log(self):
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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            AuditLog.objects.filter(
                workspace=self.workspace,
                actor=self.owner,
                action="workflow_status.created",
                entity_type="WorkflowStatus",
                entity_id=response.data["id"],
            ).exists()
        )            