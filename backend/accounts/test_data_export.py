from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Workspace,
    WorkspaceMembership,
    Project,
    ProjectMembership,
)

User = get_user_model()


class WorkspaceDataExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="export_user",
            email="export@example.com",
            password="StrongTestPassword!2026",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("workspace-data-export")

    def create_workspace(self, name, slug, role, user=None):
        workspace = Workspace.objects.create(name=name, slug=slug)
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=user or self.user,
            role=role,
        )
        return workspace

    def create_project(self, workspace, name, key):
        return Project.objects.create(
            workspace=workspace,
            name=name,
            key=key,
        )

    def test_member_export_contains_only_assigned_projects(self):
        workspace = self.create_workspace(
            "Member Workspace",
            "member-export-workspace",
            "member",
        )
        assigned = self.create_project(workspace, "Assigned Project", "ASG")
        unassigned = self.create_project(workspace, "Private Project", "PRV")

        ProjectMembership.objects.create(
            project=assigned,
            user=self.user,
        )

        captured = {}

        def fake_build(workspace, projects, include_admin_data):
            captured["project_ids"] = set(
                projects.values_list("id", flat=True)
            )
            captured["include_admin_data"] = include_admin_data
            return b"%PDF-test"

        with (
            patch(
                "accounts.data_export.build_workspace_pdf",
                side_effect=fake_build,
            ),
            patch(
                "accounts.data_export.email_workspace_exports",
                return_value={
                    "delivery": "sent",
                    "provider": "resend",
                    "provider_id": "test-export-id",
                },
            ) as send_email,
        ):
            response = self.client.post(
                self.url,
                {"workspace_id": workspace.pk},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(captured["project_ids"], {assigned.pk})
        self.assertNotIn(unassigned.pk, captured["project_ids"])
        self.assertFalse(captured["include_admin_data"])
        send_email.assert_called_once()

    def test_admin_export_contains_all_workspace_projects(self):
        workspace = self.create_workspace(
            "Admin Workspace",
            "admin-export-workspace",
            "admin",
        )
        first = self.create_project(workspace, "First Project", "FST")
        second = self.create_project(workspace, "Second Project", "SND")

        captured = {}

        def fake_build(workspace, projects, include_admin_data):
            captured["project_ids"] = set(
                projects.values_list("id", flat=True)
            )
            captured["include_admin_data"] = include_admin_data
            return b"%PDF-test"

        with (
            patch(
                "accounts.data_export.build_workspace_pdf",
                side_effect=fake_build,
            ),
            patch(
                "accounts.data_export.email_workspace_exports",
                return_value={
                    "delivery": "sent",
                    "provider": "resend",
                    "provider_id": "test-admin-export",
                },
            ),
        ):
            response = self.client.post(
                self.url,
                {"workspace_id": workspace.pk},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(captured["project_ids"], {first.pk, second.pk})
        self.assertTrue(captured["include_admin_data"])

    def test_user_cannot_export_workspace_they_do_not_belong_to(self):
        other_user = User.objects.create_user(
            username="another_user",
            email="another@example.com",
            password="StrongTestPassword!2026",
        )
        workspace = self.create_workspace(
            "Another Workspace",
            "another-export-workspace",
            "owner",
            user=other_user,
        )

        with (
            patch("accounts.data_export.build_workspace_pdf") as build_pdf,
            patch("accounts.data_export.email_workspace_exports") as send_email,
        ):
            response = self.client.post(
                self.url,
                {"workspace_id": workspace.pk},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        build_pdf.assert_not_called()
        send_email.assert_not_called()

    def test_workspace_id_is_required(self):
        with (
            patch("accounts.data_export.build_workspace_pdf") as build_pdf,
            patch("accounts.data_export.email_workspace_exports") as send_email,
        ):
            response = self.client.post(
                self.url,
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        build_pdf.assert_not_called()
        send_email.assert_not_called()

    def test_user_without_email_cannot_request_export(self):
        self.user.email = ""
        self.user.save(update_fields=["email"])

        workspace = self.create_workspace(
            "No Email Workspace",
            "no-email-export-workspace",
            "owner",
        )

        with (
            patch("accounts.data_export.build_workspace_pdf") as build_pdf,
            patch("accounts.data_export.email_workspace_exports") as send_email,
        ):
            response = self.client.post(
                self.url,
                {"workspace_id": workspace.pk},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        build_pdf.assert_not_called()
        send_email.assert_not_called()


    def test_multi_workspace_export_generates_separate_pdfs_and_sends_one_email(self):
        first_workspace = self.create_workspace(
            "First Workspace",
            "first-multi-export",
            "owner",
        )
        second_workspace = self.create_workspace(
            "Second Workspace",
            "second-multi-export",
            "admin",
        )

        first_project = self.create_project(
            first_workspace, "First Project", "ONE"
        )
        second_project = self.create_project(
            second_workspace, "Second Project", "TWO"
        )

        built = []

        def fake_build(workspace, projects, include_admin_data):
            built.append({
                "workspace_id": workspace.pk,
                "project_ids": set(projects.values_list("id", flat=True)),
                "include_admin_data": include_admin_data,
            })
            return f"%PDF-{workspace.slug}".encode()

        with (
            patch(
                "accounts.data_export.build_workspace_pdf",
                side_effect=fake_build,
            ),
            patch(
                "accounts.data_export.email_workspace_exports",
                return_value={
                    "delivery": "sent",
                    "provider": "resend",
                    "provider_id": "multi-export-test",
                    "attachment_count": 2,
                },
            ) as send_email,
        ):
            response = self.client.post(
                self.url,
                {
                    "workspace_ids": [
                        first_workspace.pk,
                        second_workspace.pk,
                    ]
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(built), 2)

        self.assertEqual(
            built[0]["workspace_id"], first_workspace.pk
        )
        self.assertEqual(
            built[0]["project_ids"], {first_project.pk}
        )
        self.assertTrue(built[0]["include_admin_data"])

        self.assertEqual(
            built[1]["workspace_id"], second_workspace.pk
        )
        self.assertEqual(
            built[1]["project_ids"], {second_project.pk}
        )
        self.assertTrue(built[1]["include_admin_data"])

        send_email.assert_called_once()
        exports = send_email.call_args.args[1]
        self.assertEqual(len(exports), 2)
        self.assertEqual(
            [item[0].pk for item in exports],
            [first_workspace.pk, second_workspace.pk],
        )
        self.assertEqual(
            [item[1] for item in exports],
            [
                f"%PDF-{first_workspace.slug}".encode(),
                f"%PDF-{second_workspace.slug}".encode(),
            ],
        )

        self.assertEqual(response.data["workspace_count"], 2)
        self.assertEqual(response.data["attachment_count"], 2)
        self.assertEqual(len(response.data["workspaces"]), 2)

    def test_multi_workspace_export_rejects_unauthorized_workspace_before_building(self):
        first_workspace = self.create_workspace(
            "Authorized Workspace",
            "authorized-multi-export",
            "owner",
        )

        other_user = User.objects.create_user(
            username="unauthorized_export_user",
            email="unauthorized@example.com",
            password="StrongTestPassword!2026",
        )
        unauthorized_workspace = self.create_workspace(
            "Unauthorized Workspace",
            "unauthorized-multi-export",
            "owner",
            user=other_user,
        )

        with (
            patch("accounts.data_export.build_workspace_pdf") as build_pdf,
            patch("accounts.data_export.email_workspace_exports") as send_email,
        ):
            response = self.client.post(
                self.url,
                {
                    "workspace_ids": [
                        first_workspace.pk,
                        unauthorized_workspace.pk,
                    ]
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        build_pdf.assert_not_called()
        send_email.assert_not_called()
