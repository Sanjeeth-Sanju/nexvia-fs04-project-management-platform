from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import (
    Workspace,
    WorkspaceMembership,
    Project,
    Board,
    Sprint,
    Issue,
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
