from .models import Notification


def create_notification(
    *,
    recipient,
    event_type,
    title,
    message,
    actor=None,
    workspace=None,
    project=None,
    target_url="",
    metadata=None,
):
    """Create one persistent in-app notification for a recipient."""
    if recipient is None or actor is not None and recipient.pk == actor.pk:
        return None

    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        workspace=workspace,
        project=project,
        event_type=event_type,
        title=title,
        message=message,
        target_url=target_url,
        metadata=metadata or {},
    )
