import os
import logging
from html import escape

import resend
from django.conf import settings

logger = logging.getLogger(__name__)


def send_workspace_invitation_email(invitation):
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured.")

    frontend_url = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173",
    ).rstrip("/")

    accept_url = (
        f"{frontend_url}/invitations/accept/"
        f"{invitation.token}"
    )

    sender = os.getenv(
        "EMAIL_FROM",
        "Nexvia <onboarding@resend.dev>",
    )

    workspace_name = escape(invitation.workspace.name)
    inviter_name = escape(str(invitation.invited_by or "Your team"))
    role = escape(invitation.role.title())
    link = escape(accept_url, quote=True)

    resend.api_key = api_key

    result = resend.Emails.send({
        "from": sender,
        "to": [invitation.email],
        "subject": f"You have been invited to {workspace_name} on Nexvia",
        "html": f"""
            <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
                <h2>You're invited to Nexvia!</h2>
                <p>{inviter_name} invited you to join
                <strong>{workspace_name}</strong> as a {role}.</p>
                <p>Accept your invitation using the button below.</p>
                <p>
                    <a href="{link}"
                       style="background:#5D866C;color:white;padding:12px 22px;
                       text-decoration:none;border-radius:6px;display:inline-block">
                       Accept invitation
                    </a>
                </p>
                <p>This invitation expires in 7 days.</p>
                <p>If you weren't expecting this invitation, you can ignore this email.</p>
                <p>— Nexvia</p>
            </div>
        """,
        "text": (
            f"{inviter_name} invited you to join {workspace_name} "
            f"on Nexvia as a {role}. Accept here: {accept_url}"
        ),
    })

    logger.info(
        "Workspace invitation email submitted to Resend. Result: %s",
        result,
    )
    return result

def send_member_access_update_email(
    recipient,
    workspace_name,
    actor_name,
    old_role,
    new_role,
    added_projects,
    removed_projects,
):
    """Send one consolidated workspace access update notification."""
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured.")

    sender = getattr(
        settings,
        "EMAIL_FROM",
        "Nexvia <notifications@nexvia.flouryn.tech>",
    )

    changes = []
    if old_role != new_role:
        changes.append(
            f"<li>Role changed from {escape(old_role.title())} "
            f"to {escape(new_role.title())}</li>"
        )

    if added_projects:
        names = ", ".join(escape(name) for name in added_projects)
        changes.append(f"<li>Projects added: {names}</li>")

    if removed_projects:
        names = ", ".join(escape(name) for name in removed_projects)
        changes.append(f"<li>Projects removed: {names}</li>")

    if not changes:
        return None

    resend.api_key = api_key

    return resend.Emails.send({
        "from": sender,
        "to": [recipient],
        "subject": f"Your workspace access was updated — {workspace_name}",
        "html": f"""
            <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
                <h2>Your workspace access was updated</h2>
                <p>{escape(actor_name)} updated your access to
                <strong>{escape(workspace_name)}</strong>.</p>
                <ul>{''.join(changes)}</ul>
                <p>If you have questions, contact your workspace owner.</p>
                <p>— Nexvia</p>
            </div>
        """,
        "text": (
            f"{actor_name} updated your access to {workspace_name}. "
            + "; ".join(
                item.replace("<li>", "").replace("</li>", "")
                for item in changes
            )
        ),
    })



def send_member_removed_email(recipient, workspace_name, actor_name):
    """Notify a member that their workspace access has been removed."""
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured.")

    sender = getattr(
        settings,
        "EMAIL_FROM",
        "Nexvia <notifications@nexvia.flouryn.tech>",
    )

    resend.api_key = api_key

    return resend.Emails.send({
        "from": sender,
        "to": [recipient],
        "subject": f"You have been removed from {workspace_name}",
        "html": f"""
            <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
                <h2>Workspace access removed</h2>
                <p>Your access to
                <strong>{escape(workspace_name)}</strong>
                has been removed by {escape(actor_name)}.</p>
                <p>If you believe this was a mistake, please contact
                the workspace owner.</p>
                <p>— Nexvia</p>
            </div>
        """,
        "text": (
            f"Your access to {workspace_name} has been removed by "
            f"{actor_name}. If you believe this was a mistake, "
            "please contact the workspace owner."
        ),
    })
