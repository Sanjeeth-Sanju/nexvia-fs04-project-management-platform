from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Notification


def serialize_notification(item):
    actor_name = None
    if item.actor_id:
        actor_name = (
            item.actor.get_full_name()
            or item.actor.get_username()
        )

    return {
        "id": item.id,
        "event_type": item.event_type,
        "title": item.title,
        "message": item.message,
        "target_url": item.target_url,
        "is_read": item.is_read,
        "read_at": item.read_at,
        "created_at": item.created_at,
        "actor": {
            "id": item.actor_id,
            "name": actor_name,
        } if item.actor_id else None,
        "workspace": {
            "id": item.workspace_id,
            "name": item.workspace.name,
        } if item.workspace_id else None,
        "project": {
            "id": item.project_id,
            "name": item.project.name,
        } if item.project_id else None,
        "metadata": item.metadata,
    }


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(
            recipient=request.user
        ).select_related("actor", "workspace", "project")

        unread_only = request.query_params.get("unread")
        if unread_only == "true":
            queryset = queryset.filter(is_read=False)

        try:
            limit = min(max(int(request.query_params.get("limit", 50)), 1), 100)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Limit must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = list(queryset[:limit])
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()

        return Response({
            "results": [serialize_notification(item) for item in items],
            "unread_count": unread_count,
        })


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({"unread_count": count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        item = get_object_or_404(
            Notification,
            pk=notification_id,
            recipient=request.user,
        )
        if not item.is_read:
            item.is_read = True
            item.read_at = timezone.now()
            item.save(update_fields=["is_read", "read_at"])

        return Response(serialize_notification(item))


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())

        return Response({"updated": updated})


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, notification_id):
        item = get_object_or_404(
            Notification,
            pk=notification_id,
            recipient=request.user,
        )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationClearAllView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted, _ = Notification.objects.filter(
            recipient=request.user
        ).delete()
        return Response({"deleted": deleted})
