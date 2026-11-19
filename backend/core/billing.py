from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from .models import (
    Workspace,
    WorkspaceMembership,
    WorkspaceInvitation,
    Project,
    Issue,
    IssueAttachment,
    WorkflowStatus,
    Subscription,
)


# None means unlimited. Subscription is individual-account based.
PLAN_LIMITS = {
    "free": {
        "workspaces": 2,
        "admin_memberships": 2,
        "member_memberships": 2,
        "members_per_workspace": 5,
        "projects_per_workspace": 3,
        "issues_per_workspace": 100,
        "storage_mb": 500,
        "audit_retention_days": 7,
        "custom_workflow_statuses": 1,
        "automations_per_workspace": 0,
        "advanced_sprints": False,
        "integrations": "basic",
        "advanced_reports": False,
        "advanced_audit_logs": False,
    },
    "pro": {
        "workspaces": 10,
        "admin_memberships": 10,
        "member_memberships": 10,
        "members_per_workspace": 25,
        "projects_per_workspace": None,
        "issues_per_workspace": None,
        "storage_mb": 10 * 1024,
        "audit_retention_days": 90,
        "custom_workflow_statuses": 10,
        "automations_per_workspace": 20,
        "advanced_sprints": True,
        "integrations": "available",
        "advanced_reports": True,
        "advanced_audit_logs": False,
    },
    "business": {
        "workspaces": None,
        "admin_memberships": None,
        "member_memberships": None,
        "members_per_workspace": 100,
        "projects_per_workspace": None,
        "issues_per_workspace": None,
        "storage_mb": 100 * 1024,
        "audit_retention_days": 365,
        "custom_workflow_statuses": None,
        "automations_per_workspace": 100,
        "advanced_sprints": True,
        "integrations": "advanced",
        "advanced_reports": True,
        "advanced_audit_logs": True,
    },
}


def get_effective_plan(user):
    subscription = Subscription.objects.filter(user=user).first()
    if not subscription or subscription.status not in ("active", "trialing"):
        return "free"
    return subscription.plan if subscription.plan in PLAN_LIMITS else "free"


def get_plan_limits(user):
    return PLAN_LIMITS[get_effective_plan(user)]


def enforce_limit(current, limit, label):
    if limit is not None and current >= limit:
        raise ValidationError({
            "detail": (
                f"You have reached your plan limit for {label}. "
                "Upgrade your subscription to increase this limit."
            ),
            "code": "plan_limit_reached",
            "limit": limit,
            "current": current,
        })


def enforce_feature(feature, allowed, message=None):
    if not allowed:
        raise ValidationError({
            "detail": message or f"This feature is not included in your plan.",
            "code": "plan_feature_unavailable",
            "feature": feature,
        })


def get_workspace_owner(workspace):
    membership = WorkspaceMembership.objects.filter(
        workspace=workspace, role="owner"
    ).select_related("user").first()
    if not membership:
        raise ValidationError({
            "detail": "This workspace has no registered owner.",
            "code": "workspace_owner_missing",
        })
    return membership.user


def check_workspace_limit(user):
    limits = get_plan_limits(user)
    current = WorkspaceMembership.objects.filter(
        user=user, role="owner"
    ).count()
    enforce_limit(current, limits["workspaces"], "owned workspaces")


def check_role_membership_limit(user, role, excluding_workspace_id=None):
    if role not in ("admin", "member"):
        return

    limits = get_plan_limits(user)
    key = "admin_memberships" if role == "admin" else "member_memberships"
    current = WorkspaceMembership.objects.filter(user=user, role=role)
    if excluding_workspace_id is not None:
        current = current.exclude(workspace_id=excluding_workspace_id)

    enforce_limit(current.count(), limits[key], f"{role} workspace memberships")


def check_project_limit(workspace):
    owner = get_workspace_owner(workspace)
    limits = get_plan_limits(owner)
    current = Project.objects.filter(workspace=workspace).count()
    enforce_limit(current, limits["projects_per_workspace"], "projects per workspace")


def check_issue_limit(project):
    owner = get_workspace_owner(project.workspace)
    limits = get_plan_limits(owner)
    # The issue quota belongs to the workspace, not an individual project.
    current = Issue.objects.filter(project__workspace=project.workspace).count()
    enforce_limit(current, limits["issues_per_workspace"], "issues per workspace")


def check_invitation_capacity(workspace):
    owner = get_workspace_owner(workspace)
    limits = get_plan_limits(owner)
    limit = limits["members_per_workspace"]
    if limit is None:
        return

    members = WorkspaceMembership.objects.filter(
        workspace=workspace
    ).exclude(role="owner").count()
    pending = WorkspaceInvitation.objects.filter(
        workspace=workspace, status="pending"
    ).count()
    enforce_limit(members + pending, limit, "workspace member seats")


def check_member_capacity(workspace):
    owner = get_workspace_owner(workspace)
    limits = get_plan_limits(owner)
    limit = limits["members_per_workspace"]
    if limit is None:
        return

    members = WorkspaceMembership.objects.filter(
        workspace=workspace
    ).exclude(role="owner").count()
    pending = WorkspaceInvitation.objects.filter(
        workspace=workspace, status="pending"
    ).count()
    enforce_limit(members + pending - 1, limit, "workspace member seats")


def check_invitee_role_capacity(user, role):
    check_role_membership_limit(user, role)


def check_workflow_status_limit(workspace):
    owner = get_workspace_owner(workspace)
    limits = get_plan_limits(owner)
    current = WorkflowStatus.objects.filter(
        workspace=workspace, is_default=False
    ).count()
    enforce_limit(
        current,
        limits["custom_workflow_statuses"],
        "custom workflow statuses per workspace",
    )


def check_storage_capacity(user, incoming_bytes):
    limits = get_plan_limits(user)
    limit_mb = limits["storage_mb"]
    if limit_mb is None:
        return

    used_bytes = 0
    attachments = IssueAttachment.objects.filter(uploaded_by=user).only("file")
    for attachment in attachments:
        try:
            if attachment.file:
                used_bytes += attachment.file.size
        except (OSError, ValueError):
            continue

    allowed_bytes = limit_mb * 1024 * 1024
    if used_bytes + incoming_bytes > allowed_bytes:
        raise ValidationError({
            "detail": "You have reached your account storage limit. Upgrade your plan or remove existing attachments.",
            "code": "plan_limit_reached",
            "feature": "storage",
            "limit_bytes": allowed_bytes,
            "used_bytes": used_bytes,
            "incoming_bytes": incoming_bytes,
        })
