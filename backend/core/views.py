from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers, status



from .models import Workspace, Project, Board, Sprint, Issue,  IssueComment, IssueAttachment, AuditLog, WorkflowStatus
from .serializers import (
    WorkspaceSerializer,
    ProjectSerializer,
    BoardSerializer,
    SprintSerializer,
    IssueSerializer,
    IssueCommentSerializer,
    IssueAttachmentSerializer,
    AuditLogSerializer,
    WorkflowStatusSerializer,
    WorkflowStatusReorderSerializer,
)


class WorkspaceListView(generics.ListAPIView):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(
            memberships__user=self.request.user
        ).distinct()


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            workspace__memberships__user=self.request.user
        ).distinct()


class BoardListCreateView(generics.ListCreateAPIView):
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Board.objects.filter(
            project__workspace__memberships__user=self.request.user
        ).distinct()


class SprintListCreateView(generics.ListCreateAPIView):
    serializer_class = SprintSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Sprint.objects.filter(
            project__workspace__memberships__user=self.request.user
        ).distinct()


class IssueListCreateView(generics.ListCreateAPIView):
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Issue.objects.filter(
            project__workspace__memberships__user=self.request.user
        ).distinct()

    def perform_create(self, serializer):
        issue = serializer.save()

        AuditLog.objects.create(
            workspace=issue.project.workspace,
            actor=self.request.user,
            action="issue.created",
            entity_type="Issue",
            entity_id=issue.id,
            details={
                "title": issue.title,
                "project": issue.project.name,
            },
        )

class IssueDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Issue.objects.filter(
            project__workspace__memberships__user=self.request.user
        ).distinct()

class IssueMoveView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        issue = get_object_or_404(
            Issue.objects.filter(
                project__workspace__memberships__user=request.user
            ),
            pk=pk,
        )

        old_status = issue.status
        old_position = issue.position

        new_status = request.data.get("status")
        new_position = request.data.get("position")

        valid_statuses = set(
            WorkflowStatus.objects.filter(
                workspace=issue.project.workspace,
            ).values_list("slug", flat=True)
        )

        if new_status not in valid_statuses:
            return Response(
                {"status": "Invalid issue status."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_position = int(new_position)
        except (TypeError, ValueError):
            return Response(
                {"position": "A valid position is required."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        if new_position < 0:
            return Response(
                {"position": "Position cannot be negative."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            source_lane = list(
                Issue.objects.filter(
                    board=issue.board,
                    status=issue.status,
                ).order_by("position", "id")
            )

            target_lane = list(
                Issue.objects.filter(
                    board=issue.board,
                    status=new_status,
                ).exclude(pk=issue.pk).order_by("position", "id")
            )

            if issue.status == new_status:
                target_lane = source_lane.copy()
                target_lane.remove(issue)

            target_position = min(new_position, len(target_lane))
            target_lane.insert(target_position, issue)

            if issue.status != new_status:
                source_lane.remove(issue)

                for index, item in enumerate(source_lane):
                    item.position = index

                Issue.objects.bulk_update(source_lane, ["position"])

            for index, item in enumerate(target_lane):
                item.status = new_status
                item.position = index

            Issue.objects.bulk_update(
                target_lane,
                ["status", "position"],
            )

            issue.refresh_from_db()

            AuditLog.objects.create(
                workspace=issue.project.workspace,
                actor=request.user,
                action="issue.moved",
                entity_type="Issue",
                entity_id=issue.id,
                details={
                    "title": issue.title,
                    "from_status": old_status,
                    "from_position": old_position,
                    "to_status": issue.status,
                    "to_position": issue.position,
                },
            )

        return Response(
            {
                "id": issue.id,
                "status": issue.status,
                "position": issue.position,
            },
            status=http_status.HTTP_200_OK,
        )
class IssueCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = IssueCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_issue(self):
        return get_object_or_404(
            Issue.objects.filter(
                project__workspace__memberships__user=self.request.user
            ).distinct(),
            pk=self.kwargs["issue_pk"],
        )

    def get_queryset(self):
        issue = self.get_issue()
        return IssueComment.objects.filter(issue=issue).select_related(
            "author",
            "issue",
        )

    def perform_create(self, serializer):
        issue = self.get_issue()

        comment = serializer.save(
            issue=issue,
            author=self.request.user,
        )

        AuditLog.objects.create(
            workspace=issue.project.workspace,
            actor=self.request.user,
            action="issue.comment.created",
            entity_type="IssueComment",
            entity_id=comment.id,
            details={
                "issue_id": issue.id,
                "issue_title": issue.title,
            },
        )

class IssueAttachmentListCreateView(generics.ListCreateAPIView):
    serializer_class = IssueAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_issue(self):
        return get_object_or_404(
            Issue.objects.filter(
                project__workspace__memberships__user=self.request.user
            ).distinct(),
            pk=self.kwargs["issue_pk"],
        )

    def get_queryset(self):
        issue = self.get_issue()
        return IssueAttachment.objects.filter(issue=issue).select_related(
            "uploaded_by",
            "issue",
        )

    def perform_create(self, serializer):
        issue = self.get_issue()
        uploaded_file = self.request.FILES.get("file")

        if uploaded_file is None:
            raise serializers.ValidationError(
                {"file": "This field is required."}
            )

        attachment = serializer.save(
            issue=issue,
            uploaded_by=self.request.user,
            filename=uploaded_file.name,
        )

        AuditLog.objects.create(
            workspace=issue.project.workspace,
            actor=self.request.user,
            action="issue.attachment.created",
            entity_type="IssueAttachment",
            entity_id=attachment.id,
            details={
                "issue_id": issue.id,
                "issue_title": issue.title,
                "filename": attachment.filename,
            },
        )

class IssueAttachmentDetailView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return IssueAttachment.objects.filter(
            issue__project__workspace__memberships__user=self.request.user
        ).distinct()

    def perform_destroy(self, instance):
        issue = instance.issue

        AuditLog.objects.create(
            workspace=issue.project.workspace,
            actor=self.request.user,
            action="issue.attachment.deleted",
            entity_type="IssueAttachment",
            entity_id=instance.id,
            details={
                "issue_id": issue.id,
                "issue_title": issue.title,
                "filename": instance.filename,
            },
        )

        instance.delete()        
class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        workspace_id = self.kwargs["workspace_pk"]

        return AuditLog.objects.filter(
            workspace_id=workspace_id,
            workspace__memberships__user=self.request.user,
        ).select_related("actor", "workspace")                

class WorkflowStatusListCreateView(generics.ListCreateAPIView):
    serializer_class = WorkflowStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_workspace(self):
        return get_object_or_404(
            Workspace.objects.filter(
                memberships__user=self.request.user,
            ).distinct(),
            pk=self.kwargs["workspace_pk"],
        )

    def get_queryset(self):
        workspace = self.get_workspace()
        return WorkflowStatus.objects.filter(
            workspace=workspace,
        ).order_by("position", "id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["workspace"] = self.get_workspace()
        return context

    def perform_create(self, serializer):
        workspace = self.get_workspace()
        workflow_status = serializer.save(workspace=workspace)

        AuditLog.objects.create(
            workspace=workspace,
            actor=self.request.user,
            action="workflow_status.created",
            entity_type="WorkflowStatus",
            entity_id=workflow_status.id,
            details={
                "name": workflow_status.name,
                "slug": workflow_status.slug,
            },
        )

class WorkflowStatusDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WorkflowStatusSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_workspace(self):
        return get_object_or_404(
            Workspace.objects.filter(
                memberships__user=self.request.user,
            ).distinct(),
            pk=self.kwargs["workspace_pk"],
        )

    def get_queryset(self):
        return WorkflowStatus.objects.filter(
            workspace=self.get_workspace(),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["workspace"] = self.get_workspace()
        return context

    def perform_update(self, serializer):
        workflow_status = serializer.save()

        AuditLog.objects.create(
            workspace=workflow_status.workspace,
            actor=self.request.user,
            action="workflow_status.updated",
            entity_type="WorkflowStatus",
            entity_id=workflow_status.id,
            details={
                "name": workflow_status.name,
                "slug": workflow_status.slug,
                "position": workflow_status.position,
                "is_completed": workflow_status.is_completed,
            },
        )

    def perform_destroy(self, instance):
        require_workspace_role(
            user=self.request.user,
            workspace=instance.workspace,
            allowed_roles=["owner", "admin"],
        )
        if instance.is_default:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"detail": "Default workflow statuses cannot be deleted."}
            )

        if Issue.objects.filter(
            project__workspace=instance.workspace,
            status=instance.slug,
        ).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"detail": "Cannot delete a workflow status currently used by issues."}
            )

        AuditLog.objects.create(
            workspace=instance.workspace,
            actor=self.request.user,
            action="workflow_status.deleted",
            entity_type="WorkflowStatus",
            entity_id=instance.id,
            details={
                "name": instance.name,
                "slug": instance.slug,
            },
        )

        instance.delete()



class WorkflowStatusReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_pk):
        workspace = get_object_or_404(
            Workspace.objects.filter(
                memberships__user=request.user,
            ).distinct(),
            pk=workspace_pk,
        )

        require_workspace_role(
            user=request.user,
            workspace=workspace,
            allowed_roles=["owner", "admin"],
        )

        serializer = WorkflowStatusReorderSerializer(
            data=request.data,
            context={"workspace": workspace},
        )
        serializer.is_valid(raise_exception=True)

        status_ids = serializer.validated_data["status_ids"]

        with transaction.atomic():
            statuses = {
                workflow_status.id: workflow_status
                for workflow_status in WorkflowStatus.objects.filter(
                    workspace=workspace,
                )
            }

            for position, status_id in enumerate(status_ids):
                statuses[status_id].position = position

            WorkflowStatus.objects.bulk_update(
                statuses.values(),
                ["position"],
            )

        ordered_statuses = WorkflowStatus.objects.filter(
            workspace=workspace,
        ).order_by("position", "id")

        return Response(
            WorkflowStatusSerializer(
                ordered_statuses,
                many=True,
                context={"workspace": workspace},
            ).data,
            status=status.HTTP_200_OK,
        )        