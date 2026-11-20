from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_member_access_update_email_task(
    self,
    recipient,
    workspace_name,
    actor_name,
    old_role,
    new_role,
    added_projects,
    removed_projects,
):
    from .email_service import send_member_access_update_email

    result = send_member_access_update_email(
        recipient=recipient,
        workspace_name=workspace_name,
        actor_name=actor_name,
        old_role=old_role,
        new_role=new_role,
        added_projects=added_projects,
        removed_projects=removed_projects,
    )
    return {"status": "sent", "result": str(result)}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_member_removed_email_task(
    self,
    recipient,
    workspace_name,
    actor_name,
):
    from .email_service import send_member_removed_email

    result = send_member_removed_email(
        recipient=recipient,
        workspace_name=workspace_name,
        actor_name=actor_name,
    )
    return {"status": "sent", "result": str(result)}


@shared_task
def celery_health_check():
    return {"status": "ok", "service": "nexvia-celery"}
