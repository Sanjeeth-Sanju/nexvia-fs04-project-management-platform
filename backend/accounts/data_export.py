from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

import resend

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


def safe(value):
    if value is None or value == "":
        return "—"
    return escape(str(value)).replace("\n", "<br/>")



def build_workspace_pdf(workspace, projects, include_admin_data):
    """Create a structured, branded Nexvia workspace report."""
    from core.models import (
        Board, Sprint, Issue, IssueComment, IssueAttachment,
        AuditLog, WorkflowStatus, WorkspaceInvitation,
    )

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether, HRFlowable,
    )
    from io import BytesIO

    buffer = BytesIO()
    page_width, page_height = A4

    green = colors.HexColor("#365B45")
    sage = colors.HexColor("#5D866C")
    pale = colors.HexColor("#EAF0EB")
    cream = colors.HexColor("#F6F5F0")
    ink = colors.HexColor("#26332B")
    muted = colors.HexColor("#718078")
    border = colors.HexColor("#DFE5DE")
    white = colors.white

    margin = 17 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
        title=f"{workspace.name} - Nexvia Workspace Report",
        author="Nexvia",
        subject="Workspace data export",
    )
    width = page_width - 2 * margin

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Brand",
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=green,
        alignment=TA_LEFT,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=25,
        textColor=ink,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Section",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=green,
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="Subsection",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=ink,
        spaceBefore=9,
        spaceAfter=5,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="BodyN",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=ink,
        spaceAfter=3,
        wordWrap="CJK",
    ))
    styles.add(ParagraphStyle(
        name="SmallN",
        fontName="Helvetica",
        fontSize=7.2,
        leading=9.5,
        textColor=muted,
        wordWrap="CJK",
    ))
    styles.add(ParagraphStyle(
        name="CellN",
        fontName="Helvetica",
        fontSize=7.2,
        leading=9.5,
        textColor=ink,
        wordWrap="CJK",
    ))
    styles.add(ParagraphStyle(
        name="CellHeadN",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=white,
    ))
    styles.add(ParagraphStyle(
        name="MetricN",
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=22,
        textColor=green,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="MetricLabelN",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=muted,
        alignment=TA_CENTER,
    ))

    P = lambda value, style="BodyN": Paragraph(safe(value), styles[style])

    projects = list(projects.order_by("name"))
    project_data = []
    issue_count = 0
    comment_count = 0
    attachment_count = 0
    board_count = 0
    sprint_count = 0

    for project in projects:
        boards = list(Board.objects.filter(project=project).order_by("name"))
        sprints = list(Sprint.objects.filter(project=project).order_by("created_at"))
        issues = list(
            Issue.objects.filter(project=project)
            .select_related("assignee", "board", "sprint")
            .order_by("created_at")
        )
        board_count += len(boards)
        sprint_count += len(sprints)
        issue_count += len(issues)

        for issue in issues:
            comment_count += IssueComment.objects.filter(issue=issue).count()
            attachment_count += IssueAttachment.objects.filter(issue=issue).count()

        project_data.append((project, boards, sprints, issues))

    story = []

    # Branded report cover/header.
    brand_block = Table(
        [[P("NEXVIA", "Brand"), P("WORKSPACE REPORT", "SmallN")]],
        colWidths=[width * .62, width * .38],
    )
    brand_block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale),
        ("BOX", (0, 0), (-1, -1), .6, border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 13),
        ("RIGHTPADDING", (0, 0), (-1, -1), 13),
        ("TOPPADDING", (0, 0), (-1, -1), 13),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
    ]))
    story += [
        brand_block,
        Spacer(1, 17),
        P("Workspace Data Export", "ReportTitle"),
        P(workspace.name, "Section"),
        P(
            "A snapshot of the workspace information and records accessible "
            "to the requesting account.",
        ),
        Spacer(1, 10),
    ]

    meta_rows = [
        [P("<b>Workspace ID</b>"), P(workspace.pk),
         P("<b>Workspace slug</b>"), P(workspace.slug)],
        [P("<b>Created</b>"), P(workspace.created_at),
         P("<b>Generated</b>"), P(timezone.now())],
        [P("<b>Export scope</b>"), P(
            "All workspace projects" if include_admin_data
            else "Projects and records accessible to your account"
        ), P("<b>Access level</b>"), P(
            "Administrator" if include_admin_data else "Member"
        )],
    ]
    meta = Table(meta_rows, colWidths=[width*.15, width*.35, width*.15, width*.35])
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cream),
        ("GRID", (0, 0), (-1, -1), .4, border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [meta, Spacer(1, 13)]

    metrics = [
        (len(projects), "PROJECTS"),
        (board_count, "BOARDS"),
        (sprint_count, "SPRINTS"),
        (issue_count, "ISSUES"),
    ]
    metric_cells = []
    for number, label in metrics:
        metric_cells.append([
            P(number, "MetricN"),
            P(label, "MetricLabelN"),
        ])
    metric_table = Table(
        [[Table([[cell]], colWidths=[width/4 - 8]) for cell in metric_cells]],
        colWidths=[width/4] * 4,
    )
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), pale),
        ("BOX", (0, 0), (-1, -1), .5, border),
        ("INNERGRID", (0, 0), (-1, -1), .5, white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [metric_table, Spacer(1, 9)]
    story.append(P(
        f"{comment_count} comments · {attachment_count} attachment records "
        "(metadata only)",
        "SmallN",
    ))

    # Project index.
    story.append(P("Project overview", "Section"))
    if project_data:
        rows = [[
            P("PROJECT", "CellHeadN"),
            P("KEY", "CellHeadN"),
            P("STATUS", "CellHeadN"),
            P("BOARDS", "CellHeadN"),
            P("ISSUES", "CellHeadN"),
        ]]
        for project, boards, sprints, issues in project_data:
            rows.append([
                P(project.name, "CellN"),
                P(project.key, "CellN"),
                P(project.get_status_display(), "CellN"),
                P(len(boards), "CellN"),
                P(len(issues), "CellN"),
            ])
        index = Table(rows, colWidths=[
            width*.34, width*.14, width*.22, width*.14, width*.16
        ], repeatRows=1)
        index.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), green),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, cream]),
            ("GRID", (0, 0), (-1, -1), .4, border),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(index)
    else:
        story.append(P("No accessible projects were found in this workspace."))

    # Detailed project records.
    for project, boards, sprints, issues in project_data:
        story.append(PageBreak())
        story.append(P(f"{project.key}  /  {project.name}", "ReportTitle"))
        story.append(P(
            f"Status: {project.get_status_display()}  ·  "
            f"Created: {project.created_at}",
            "SmallN",
        ))
        story.append(HRFlowable(width="100%", color=border, thickness=.7, spaceAfter=8))
        story.append(P("Project description", "Subsection"))
        story.append(P(project.description))

        story.append(P(f"Boards ({len(boards)})", "Subsection"))
        if boards:
            board_rows = [[P("BOARD", "CellHeadN"), P("CREATED", "CellHeadN")]]
            board_rows += [[P(b.name, "CellN"), P(b.created_at, "CellN")] for b in boards]
            t = Table(board_rows, colWidths=[width*.65, width*.35], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), sage),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, cream]),
                ("GRID", (0, 0), (-1, -1), .4, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
        else:
            story.append(P("No boards." , "SmallN"))

        story.append(P(f"Sprints ({len(sprints)})", "Subsection"))
        if sprints:
            sprint_rows = [[
                P("SPRINT", "CellHeadN"), P("STATUS", "CellHeadN"),
                P("DATES", "CellHeadN"), P("GOAL", "CellHeadN"),
            ]]
            for sprint in sprints:
                sprint_rows.append([
                    P(sprint.name, "CellN"),
                    P(sprint.get_status_display(), "CellN"),
                    P(f"{sprint.start_date or '—'} – {sprint.end_date or '—'}", "CellN"),
                    P(sprint.goal, "CellN"),
                ])
            t = Table(sprint_rows, colWidths=[
                width*.22, width*.18, width*.25, width*.35
            ], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), sage),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, cream]),
                ("GRID", (0, 0), (-1, -1), .4, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
        else:
            story.append(P("No sprints.", "SmallN"))

        story.append(P(f"Issue register ({len(issues)})", "Subsection"))
        if issues:
            issue_rows = [[
                P("ISSUE", "CellHeadN"),
                P("STATUS", "CellHeadN"),
                P("PRIORITY", "CellHeadN"),
                P("ASSIGNEE", "CellHeadN"),
            ]]
            for issue in issues:
                assignee = issue.assignee.username if issue.assignee_id else "Unassigned"
                issue_rows.append([
                    P(f"{project.key}-{issue.pk}: {issue.title}", "CellN"),
                    P(issue.get_status_display(), "CellN"),
                    P(issue.get_priority_display(), "CellN"),
                    P(assignee, "CellN"),
                ])
            t = Table(issue_rows, colWidths=[
                width*.43, width*.19, width*.17, width*.21
            ], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, cream]),
                ("GRID", (0, 0), (-1, -1), .4, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)

        for issue in issues:
            story.append(P(
                f"{project.key}-{issue.pk} · {issue.title}",
                "Subsection",
            ))
            story.append(P(
                f"Type: {issue.get_issue_type_display()}  ·  "
                f"Board: {issue.board.name}  ·  "
                f"Sprint: {issue.sprint.name if issue.sprint_id else '—'}",
                "SmallN",
            ))
            story.append(P(f"Description: {issue.description}"))
            story.append(P(
                f"Created: {issue.created_at}  ·  Updated: {issue.updated_at}",
                "SmallN",
            ))

            comments = list(
                IssueComment.objects.filter(issue=issue)
                .select_related("author").order_by("created_at")
            )
            if comments:
                story.append(P("Comments", "SmallN"))
                for comment in comments:
                    author = comment.author.username if comment.author_id else "Deleted user"
                    story.append(P(
                        f"<b>{safe(author)}</b> · {safe(comment.created_at)}<br/>"
                        f"{safe(comment.body)}"
                    ))

            attachments = list(
                IssueAttachment.objects.filter(issue=issue)
                .select_related("uploaded_by").order_by("uploaded_at")
            )
            if attachments:
                story.append(P("Attachments · metadata only", "SmallN"))
                for attachment in attachments:
                    uploader = (
                        attachment.uploaded_by.username
                        if attachment.uploaded_by_id else "Deleted user"
                    )
                    story.append(P(
                        f"{safe(attachment.filename)} · "
                        f"Uploaded by {safe(uploader)} · {safe(attachment.uploaded_at)}",
                        "SmallN",
                    ))

    # Workspace-wide administrative appendix is only included for admins/owners.
    if include_admin_data:
        story.append(PageBreak())
        story.append(P("Workspace administration", "ReportTitle"))
        story.append(P(
            "Administrative configuration and workspace-wide records.",
            "BodyN",
        ))

        story.append(P("Workflow statuses", "Section"))
        statuses = list(
            WorkflowStatus.objects.filter(workspace=workspace).order_by("position")
        )
        if statuses:
            rows = [[
                P("STATUS", "CellHeadN"), P("SLUG", "CellHeadN"),
                P("DEFAULT", "CellHeadN"), P("COMPLETED", "CellHeadN"),
            ]]
            rows += [[
                P(x.name, "CellN"), P(x.slug, "CellN"),
                P("Yes" if x.is_default else "No", "CellN"),
                P("Yes" if x.is_completed else "No", "CellN"),
            ] for x in statuses]
            t = Table(rows, colWidths=[width*.4, width*.3, width*.15, width*.15], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, cream]),
                ("GRID", (0, 0), (-1, -1), .4, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
        else:
            story.append(P("No workflow statuses."))

        story.append(P("Invitations · tokens excluded", "Section"))
        invitations = list(
            WorkspaceInvitation.objects.filter(workspace=workspace).order_by("-created_at")
        )
        if invitations:
            rows = [[
                P("EMAIL", "CellHeadN"), P("ROLE", "CellHeadN"),
                P("STATUS", "CellHeadN"), P("CREATED", "CellHeadN"),
                P("EXPIRES", "CellHeadN"),
            ]]
            for item in invitations:
                rows.append([
                    P(item.email, "CellN"),
                    P(item.get_role_display(), "CellN"),
                    P(item.get_status_display(), "CellN"),
                    P(item.created_at, "CellN"),
                    P(item.expires_at, "CellN"),
                ])
            t = Table(rows, colWidths=[
                width*.28, width*.16, width*.16, width*.2, width*.2
            ], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, cream]),
                ("GRID", (0, 0), (-1, -1), .4, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
        else:
            story.append(P("No invitations."))

        story.append(P("Audit history", "Section"))
        logs = list(
            AuditLog.objects.filter(workspace=workspace)
            .select_related("actor").order_by("-created_at")
        )
        if logs:
            rows = [[
                P("DATE", "CellHeadN"), P("ACTOR", "CellHeadN"),
                P("ACTION", "CellHeadN"), P("ENTITY", "CellHeadN"),
                P("DETAILS", "CellHeadN"),
            ]]
            for log in logs:
                actor = log.actor.username if log.actor_id else "Deleted user"
                rows.append([
                    P(log.created_at, "CellN"),
                    P(actor, "CellN"),
                    P(log.action, "CellN"),
                    P(f"{log.entity_type} #{log.entity_id}", "CellN"),
                    P(log.details, "CellN"),
                ])
            t = Table(rows, colWidths=[
                width*.19, width*.16, width*.17, width*.19, width*.29
            ], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, cream]),
                ("GRID", (0, 0), (-1, -1), .4, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
        else:
            story.append(P("No audit history."))

    def draw_page(canvas, document):
        canvas.saveState()
        # Running header
        canvas.setStrokeColor(border)
        canvas.setLineWidth(.6)
        canvas.line(margin, page_height - 15 * mm, page_width - margin, page_height - 15 * mm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(green)
        canvas.drawString(margin, page_height - 12 * mm, "NEXVIA")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(muted)
        canvas.drawRightString(
            page_width - margin, page_height - 12 * mm,
            f"{workspace.name}  ·  WORKSPACE EXPORT"
        )
        # Footer
        canvas.setStrokeColor(border)
        canvas.line(margin, 14 * mm, page_width - margin, 14 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(muted)
        canvas.drawString(margin, 9 * mm, "Nexvia · Confidential workspace export")
        canvas.drawRightString(
            page_width - margin, 9 * mm, f"Page {document.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer.getvalue()


def email_workspace_exports(user, exports):
    """Email multiple workspace PDFs in one message.

    exports is an iterable of (workspace, pdf_bytes) pairs.
    """
    if not user.email:
        raise ValueError("Your account does not have a registered email address.")

    exports = list(exports)
    if not exports:
        raise ValueError("Select at least one workspace to export.")

    attachments = [
        (f"nexvia-{workspace.slug}-export.pdf", pdf_bytes, "application/pdf")
        for workspace, pdf_bytes in exports
    ]

    workspace_names = [workspace.name for workspace, _ in exports]
    subject = (
        f"Your Nexvia workspace exports ({len(exports)} workspaces)"
        if len(exports) > 1
        else f"Your Nexvia workspace export: {workspace_names[0]}"
    )

    names_text = "\\n".join(f"- {name}" for name in workspace_names)
    message = (
        "Your requested Nexvia workspace data exports are attached.\\n\\n"
        f"Workspaces included:\\n{names_text}\\n\\n"
        "Each PDF contains records accessible to your account at the time "
        "the export was generated."
    )

    api_key = getattr(settings, "RESEND_API_KEY", "")
    sender = getattr(settings, "EMAIL_FROM", "Nexvia <onboarding@resend.dev>")

    if api_key:
        import base64

        resend.api_key = api_key
        result = resend.Emails.send({
            "from": sender,
            "to": [user.email],
            "subject": subject,
            "text": message,
            "attachments": [
                {
                    "filename": filename,
                    "content": base64.b64encode(content).decode("ascii"),
                }
                for filename, content, _mime in attachments
            ],
        })
        return {
            "delivery": "sent",
            "provider": "resend",
            "provider_id": result.get("id") if isinstance(result, dict) else None,
            "attachment_count": len(attachments),
        }

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=sender,
        to=[user.email],
    )
    for filename, content, mime_type in attachments:
        email.attach(filename, content, mime_type)

    sent_count = email.send(fail_silently=False)
    if sent_count != 1:
        raise RuntimeError("The email backend did not accept the export email.")

    return {
        "delivery": "accepted_by_email_backend",
        "provider": "django",
        "provider_id": None,
        "attachment_count": len(attachments),
    }


def email_workspace_export(user, workspace, pdf_bytes):
    """Backward-compatible single-workspace export email."""
    return email_workspace_exports(user, [(workspace, pdf_bytes)])

