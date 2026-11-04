from rest_framework.exceptions import PermissionDenied

from .models import WorkspaceMembership


def require_workspace_role(user, workspace, allowed_roles):
    """
    Raise PermissionDenied unless the user has an allowed role
    in the given workspace.
    """
    membership = WorkspaceMembership.objects.filter(
        workspace=workspace,
        user=user,
    ).first()

    if membership is None:
        raise PermissionDenied(
            "You do not have access to this workspace."
        )

    if membership.role not in allowed_roles:
        raise PermissionDenied(
            "Your workspace role does not allow this action."
        )

    return membership