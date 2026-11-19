from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from core.models import (
    Workspace,
    WorkspaceMembership,
    Project,
    Board,
    Issue,
    WorkspaceInvitation,
    AuditLog,
)

from accounts.data_export import (
    build_workspace_pdf,
    email_workspace_export,
    email_workspace_exports,
)

User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RESEND_API_KEY="",
    EMAIL_FROM="Nexvia <exports@example.com>",
)
class WorkspaceExportDocumentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pdf_user",
            email="pdf@example.com",
            password="StrongTestPassword!2026",
        )
        self.workspace = Workspace.objects.create(
            name="PDF Test Workspace",
            slug="pdf-test-workspace",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.user,
            role="owner",
        )
        self.project = Project.objects.create(
            workspace=self.workspace,
            name="PDF Test Project",
            key="PDF",
            description="A project for PDF export testing",
        )
        self.board = Board.objects.create(
            project=self.project,
            name="Main Board",
        )
        Issue.objects.create(
            project=self.project,
            board=self.board,
            title="PDF Test Issue",
            description="Issue description for export",
        )

    def test_pdf_is_generated_successfully(self):
        pdf = build_workspace_pdf(
            self.workspace,
            Project.objects.filter(pk=self.project.pk),
            include_admin_data=True,
        )

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)

    def test_admin_pdf_differs_from_member_pdf(self):
        projects = Project.objects.filter(pk=self.project.pk)

        admin_pdf = build_workspace_pdf(
            self.workspace,
            projects,
            include_admin_data=True,
        )
        member_pdf = build_workspace_pdf(
            self.workspace,
            projects,
            include_admin_data=False,
        )

        self.assertTrue(admin_pdf.startswith(b"%PDF"))
        self.assertTrue(member_pdf.startswith(b"%PDF"))
        self.assertNotEqual(admin_pdf, member_pdf)

    def test_invitation_token_is_not_added_to_pdf_story(self):
        invitation = WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            email="invited@example.com",
            role="member",
            invited_by=self.user,
        )

        pdf = build_workspace_pdf(
            self.workspace,
            Project.objects.filter(pk=self.project.pk),
            include_admin_data=True,
        )

        # The actual secret token must never appear in the generated PDF.
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertNotIn(invitation.token.encode("utf-8"), pdf)

    def test_email_backend_receives_pdf_attachment(self):
        pdf = build_workspace_pdf(
            self.workspace,
            Project.objects.filter(pk=self.project.pk),
            include_admin_data=True,
        )

        result = email_workspace_export(
            self.user,
            self.workspace,
            pdf,
        )

        self.assertEqual(result["provider"], "django")
        self.assertEqual(result["delivery"], "accepted_by_email_backend")
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [self.user.email])
        self.assertIn("workspace export", sent_email.subject.lower())

        attachments = sent_email.attachments
        self.assertEqual(len(attachments), 1)

        filename, content, mimetype = attachments[0]
        self.assertTrue(filename.endswith(".pdf"))
        self.assertEqual(mimetype, "application/pdf")
        self.assertTrue(content.startswith(b"%PDF"))

    def test_admin_pdf_includes_workspace_audit_data(self):
        AuditLog.objects.create(
            workspace=self.workspace,
            actor=self.user,
            action="test_export_action",
            entity_type="project",
            entity_id=self.project.pk,
            details={"source": "export-test"},
        )

        admin_pdf = build_workspace_pdf(
            self.workspace,
            Project.objects.filter(pk=self.project.pk),
            include_admin_data=True,
        )
        member_pdf = build_workspace_pdf(
            self.workspace,
            Project.objects.filter(pk=self.project.pk),
            include_admin_data=False,
        )

        self.assertNotEqual(admin_pdf, member_pdf)


    def test_multiple_workspace_pdfs_are_sent_in_one_email(self):
        second_workspace = Workspace.objects.create(
            name="Second Export Workspace",
            slug="second-export-workspace",
        )
        WorkspaceMembership.objects.create(
            workspace=second_workspace,
            user=self.user,
            role="admin",
        )

        first_pdf = b"%PDF-first-workspace"
        second_pdf = b"%PDF-second-workspace"

        result = email_workspace_exports(
            self.user,
            [
                (self.workspace, first_pdf),
                (second_workspace, second_pdf),
            ],
        )

        self.assertEqual(result["provider"], "django")
        self.assertEqual(
            result["delivery"],
            "accepted_by_email_backend",
        )
        self.assertEqual(result["attachment_count"], 2)
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [self.user.email])
        self.assertIn("2 workspaces", sent_email.subject.lower())

        attachments = sent_email.attachments
        self.assertEqual(len(attachments), 2)

        self.assertEqual(
            attachments[0],
            (
                "nexvia-pdf-test-workspace-export.pdf",
                first_pdf,
                "application/pdf",
            ),
        )
        self.assertEqual(
            attachments[1],
            (
                "nexvia-second-export-workspace-export.pdf",
                second_pdf,
                "application/pdf",
            ),
        )

        self.assertIn(self.workspace.name, sent_email.body)
        self.assertIn(second_workspace.name, sent_email.body)
