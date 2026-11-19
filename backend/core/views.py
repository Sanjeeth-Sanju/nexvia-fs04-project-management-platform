from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers, status
from .billing import (
    check_workspace_limit,
    check_project_limit,
    check_issue_limit,
    check_invitation_capacity,
    check_member_capacity,
    check_invitee_role_capacity,
    check_role_membership_limit,
    check_workflow_status_limit,
    check_storage_capacity,
    get_plan_limits,
    get_workspace_owner,
    enforce_feature,
)



from .models import WorkspaceMembership, Workspace, Project, ProjectMembership, Board, Sprint, Issue, IssueComment, IssueAttachment, AuditLog, WorkflowStatus
from .permissions import require_workspace_role
from .serializers import (
    WorkspaceSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    BoardSerializer,
    SprintSerializer,
    IssueSerializer,
    IssueCommentSerializer,
    IssueAttachmentSerializer,
    AuditLogSerializer,
    WorkflowStatusSerializer,
    WorkflowStatusReorderSerializer,
)


class WorkspaceListView(generics.ListCreateAPIView):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(
            memberships__user=self.request.user
        ).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        check_workspace_limit(self.request.user)
        workspace = serializer.save()

        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.request.user,
            role="owner",
        )




def accessible_projects_for_user(user):
    owner_admin_workspace_ids = WorkspaceMembership.objects.filter(
        user=user, role__in=["owner", "admin"]
    ).values_list("workspace_id", flat=True)

    member_workspace_ids = WorkspaceMembership.objects.filter(
        user=user, role="member"
    ).values_list("workspace_id", flat=True)

    assigned_project_ids = ProjectMembership.objects.filter(
        user=user
    ).values_list("project_id", flat=True)

    return Project.objects.filter(
        Q(workspace_id__in=owner_admin_workspace_ids)
        | Q(
            workspace_id__in=member_workspace_ids,
            id__in=assigned_project_ids,
        )
    ).distinct()


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return accessible_projects_for_user(self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        check_project_limit(serializer.validated_data["workspace"])
        project = serializer.save()
        AuditLog.objects.create(
            workspace=project.workspace, actor=self.request.user,
            action="project.created", entity_type="Project", entity_id=project.id,
            details={"project_name": project.name, "project_key": project.key},
        )



class ProjectUpdateView(generics.UpdateAPIView):
    serializer_class = ProjectUpdateSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["patch", "options", "head"]

    def get_queryset(self):
        return accessible_projects_for_user(self.request.user)

    def get_object(self):
        project = super().get_object()

        is_owner_or_admin = WorkspaceMembership.objects.filter(
            workspace=project.workspace,
            user=self.request.user,
            role__in=["owner", "admin"],
        ).exists()

        if not is_owner_or_admin:
            raise PermissionDenied(
                "Only workspace owners and admins can edit projects."
            )

        if project.status == "completed":
            raise PermissionDenied("Completed projects are read-only.")

        return project

    @transaction.atomic
    def perform_update(self, serializer):
        project = serializer.save()
        AuditLog.objects.create(
            workspace=project.workspace,
            actor=self.request.user,
            action="project.updated",
            entity_type="Project",
            entity_id=project.id,
            details={
                "project_name": project.name,
                "project_key": project.key,
            },
        )


class ProjectLifecycleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        new_status = request.data.get("status")

        if new_status not in ["active", "completed"]:
            raise serializers.ValidationError({
                "status": "Status must be either 'active' or 'completed'."
            })

        with transaction.atomic():
            accessible_project = get_object_or_404(
                accessible_projects_for_user(request.user),
                pk=pk,
            )
            project = get_object_or_404(
                Project.objects.select_for_update(),
                pk=accessible_project.pk,
            )

            is_owner_or_admin = WorkspaceMembership.objects.filter(
                workspace=project.workspace,
                user=request.user,
                role__in=["owner", "admin"],
            ).exists()

            if not is_owner_or_admin:
                raise PermissionDenied(
                    "Only workspace owners and admins can change project status."
                )

            if project.status == new_status:
                return Response(ProjectSerializer(
                    project,
                    context={"request": request},
                ).data)

            if new_status == "completed":
                project.status = "completed"
                project.completed_at = timezone.now()
                project.completed_by = request.user
                action = "project.completed"
            else:
                project.status = "active"
                project.completed_at = None
                project.completed_by = None
                action = "project.reopened"

            project.save(update_fields=[
                "status",
                "completed_at",
                "completed_by",
            ])

            AuditLog.objects.create(
                workspace=project.workspace,
                actor=request.user,
                action=action,
                entity_type="project",
                entity_id=project.id,
                details={"project_name": project.name},
            )

        return Response(ProjectSerializer(
            project,
            context={"request": request},
        ).data)


class ProjectDestroyView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            workspace__memberships__user=self.request.user
        ).distinct()

    def perform_destroy(self, instance):
        is_owner = WorkspaceMembership.objects.filter(
            workspace=instance.workspace,
            user=self.request.user,
            role="owner",
        ).exists()

        if not is_owner:
            raise PermissionDenied(
                "Only workspace owners can delete projects."
            )

        AuditLog.objects.create(
            workspace=instance.workspace, actor=self.request.user,
            action="project.deleted", entity_type="Project", entity_id=instance.id,
            details={"project_name": instance.name, "project_key": instance.key},
        )
        instance.delete()


def ensure_project_active(project):
    if project.status == "completed":
        raise serializers.ValidationError(
            {"detail": "This project is completed and read-only. Reopen it to make changes."}
        )


def ensure_issue_active(issue):
    if WorkflowStatus.objects.filter(
        workspace=issue.project.workspace,
        slug=issue.status,
        is_completed=True,
    ).exists():
        raise serializers.ValidationError({
            "detail": "This issue is completed and read-only. An owner or admin must reopen it first."
        })


class BoardListCreateView(generics.ListCreateAPIView):
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        ensure_project_active(project)
        serializer.save()

    def get_queryset(self):
        return Board.objects.filter(
            project__in=accessible_projects_for_user(self.request.user)
        ).distinct()


class SprintListCreateView(generics.ListCreateAPIView):
    serializer_class = SprintSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Sprint.objects.filter(
            project__in=accessible_projects_for_user(self.request.user)
        ).select_related("project").distinct()

        project_id = self.request.query_params.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        ensure_project_active(project)
        sprint = serializer.save()

        AuditLog.objects.create(
            workspace=project.workspace,
            actor=self.request.user,
            action="sprint.created",
            entity_type="Sprint",
            entity_id=sprint.id,
            details={"name": sprint.name, "project_id": project.id},
        )


class SprintDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SprintSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Sprint.objects.filter(
            project__in=accessible_projects_for_user(self.request.user)
        ).select_related("project").distinct()

    def perform_update(self, serializer):
        sprint = self.get_object()
        require_workspace_role(
            user=self.request.user,
            workspace=sprint.project.workspace,
            allowed_roles=["owner", "admin"],
        )
        ensure_project_active(sprint.project)

        if sprint.status == "completed":
            changes = serializer.validated_data
            if set(changes.keys()) != {"status"} or changes.get("status") != "active":
                raise serializers.ValidationError(
                    "Reopen the completed sprint before editing it."
                )

        updated = serializer.save()
        AuditLog.objects.create(
            workspace=updated.project.workspace,
            actor=self.request.user,
            action="sprint.updated",
            entity_type="Sprint",
            entity_id=updated.id,
            details={"name": updated.name, "status": updated.status},
        )

    def perform_destroy(self, instance):
        require_workspace_role(
            user=self.request.user,
            workspace=instance.project.workspace,
            allowed_roles=["owner", "admin"],
        )
        ensure_project_active(instance.project)

        if instance.status == "completed":
            raise serializers.ValidationError(
                "Reopen the completed sprint before deleting it."
            )

        AuditLog.objects.create(
            workspace=instance.project.workspace,
            actor=self.request.user,
            action="sprint.deleted",
            entity_type="Sprint",
            entity_id=instance.id,
            details={"name": instance.name, "project_id": instance.project_id},
        )
        instance.delete()


class IssueListCreateView(generics.ListCreateAPIView):
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Issue.objects.filter(
            project__in=accessible_projects_for_user(self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        ensure_project_active(project)
        check_issue_limit(project)
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
            project__in=accessible_projects_for_user(self.request.user)
        ).distinct()

    def perform_update(self, serializer):
        instance = serializer.instance
        ensure_project_active(instance.project)
        ensure_issue_active(instance)
        require_workspace_role(
            user=self.request.user,
            workspace=instance.project.workspace,
            allowed_roles=["owner", "admin"],
        )
        previous = {
            "title": instance.title,
            "description": instance.description,
            "issue_type": instance.issue_type,
            "priority": instance.priority,
            "assignee_id": instance.assignee_id,
        }
        issue = serializer.save()
        changes = {
            key: {"from": value, "to": getattr(issue, key)}
            for key, value in previous.items()
            if value != getattr(issue, key)
        }
        if changes:
            AuditLog.objects.create(
                workspace=issue.project.workspace,
                actor=self.request.user,
                action="issue.updated",
                entity_type="Issue",
                entity_id=issue.id,
                details={"title": issue.title, "changes": changes},
            )

    def perform_destroy(self, instance):
        ensure_project_active(instance.project)
        ensure_issue_active(instance)
        require_workspace_role(
            user=self.request.user,
            workspace=instance.project.workspace,
            allowed_roles=["owner", "admin"],
        )
        AuditLog.objects.create(
            workspace=instance.project.workspace,
            actor=self.request.user,
            action="issue.deleted",
            entity_type="Issue",
            entity_id=instance.id,
            details={"title": instance.title, "project_id": instance.project_id},
        )
        instance.delete()

class IssueMoveView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        issue = get_object_or_404(
            Issue.objects.filter(
                project__in=accessible_projects_for_user(request.user)
            ),
            pk=pk,
        )

        ensure_project_active(issue.project)

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

        completed_statuses = set(
            WorkflowStatus.objects.filter(
                workspace=issue.project.workspace,
                is_completed=True,
            ).values_list("slug", flat=True)
        )

        involves_completed_status = (
            issue.status in completed_statuses
            or new_status in completed_statuses
        )

        if involves_completed_status:
            require_workspace_role(
                user=request.user,
                workspace=issue.project.workspace,
                allowed_roles=["owner", "admin"],
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
                project__in=accessible_projects_for_user(self.request.user)
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
        ensure_project_active(issue.project)
        ensure_issue_active(issue)

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

class IssueCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = IssueCommentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return IssueComment.objects.filter(
            issue__project__in=accessible_projects_for_user(self.request.user)
        ).select_related("author", "issue", "issue__project").distinct()

    def _require_author(self, instance):
        if instance.author_id != self.request.user.id:
            raise PermissionDenied("You can only edit or delete your own comments.")
        ensure_project_active(instance.issue.project)
        ensure_issue_active(instance.issue)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        self._require_author(instance)
        response = super().update(request, *args, **kwargs)
        AuditLog.objects.create(
            workspace=instance.issue.project.workspace,
            actor=request.user,
            action="issue.comment.updated",
            entity_type="IssueComment",
            entity_id=instance.id,
            details={"issue_id": instance.issue_id, "issue_title": instance.issue.title},
        )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._require_author(instance)
        AuditLog.objects.create(
            workspace=instance.issue.project.workspace,
            actor=request.user,
            action="issue.comment.deleted",
            entity_type="IssueComment",
            entity_id=instance.id,
            details={"issue_id": instance.issue_id, "issue_title": instance.issue.title},
        )
        return super().destroy(request, *args, **kwargs)


class IssueAttachmentListCreateView(generics.ListCreateAPIView):
    serializer_class = IssueAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_issue(self):
        return get_object_or_404(
            Issue.objects.filter(
                project__in=accessible_projects_for_user(self.request.user)
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
        ensure_project_active(issue.project)
        ensure_issue_active(issue)
        uploaded_file = self.request.FILES.get("file")

        if uploaded_file is None:
            raise serializers.ValidationError(
                {"file": "This field is required."}
            )

        check_storage_capacity(self.request.user, uploaded_file.size)
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
            issue__project__in=accessible_projects_for_user(self.request.user)
        ).distinct()

    def perform_destroy(self, instance):
        issue = instance.issue
        ensure_project_active(issue.project)
        ensure_issue_active(issue)

        membership = WorkspaceMembership.objects.filter(
            workspace=issue.project.workspace,
            user=self.request.user,
        ).first()

        if membership is None:
            raise PermissionDenied("You do not have access to this workspace.")

        is_owner_or_admin = membership.role in ["owner", "admin"]
        is_uploader = instance.uploaded_by_id == self.request.user.id

        if not (is_owner_or_admin or is_uploader):
            raise PermissionDenied(
                "You can only delete attachments you uploaded."
            )

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
        user = self.request.user

        membership = WorkspaceMembership.objects.filter(
            workspace_id=workspace_id,
            user=user,
        ).only("role").first()

        if membership is None:
            return AuditLog.objects.none()

        workspace = Workspace.objects.get(pk=workspace_id)
        workspace_owner = get_workspace_owner(workspace)
        limits = get_plan_limits(workspace_owner)
        retention_days = limits["audit_retention_days"]
        from django.utils import timezone
        from datetime import timedelta

        logs = AuditLog.objects.filter(
            workspace_id=workspace_id,
            created_at__gte=timezone.now() - timedelta(days=retention_days),
        )

        if membership.role in ["owner", "admin"]:
            return logs.select_related("actor", "workspace")

        accessible_project_ids = accessible_projects_for_user(user).filter(
            workspace_id=workspace_id,
        ).values_list("id", flat=True)

        accessible_issue_ids = Issue.objects.filter(
            project_id__in=accessible_project_ids,
        ).values_list("id", flat=True)

        issue_logs = logs.filter(
            entity_type="Issue",
            entity_id__in=accessible_issue_ids,
        )

        from django.db.models import IntegerField
        from django.db.models.fields.json import KeyTextTransform
        from django.db.models.functions import Cast

        accessible_issue_id_list = list(accessible_issue_ids)

        related_logs = logs.annotate(
            related_issue_id=Cast(
                KeyTextTransform("issue_id", "details"),
                output_field=IntegerField(),
            )
        ).filter(
            related_issue_id__in=accessible_issue_id_list,
        )

        membership_logs = logs.filter(
            entity_type="WorkspaceMembership",
            action__startswith="workspace.member_",
        )

        return (
            issue_logs | related_logs | membership_logs
        ).distinct().select_related(
            "actor", "workspace"
        )

class WorkflowStatusListCreateView(generics.ListCreateAPIView):
    serializer_class = WorkflowStatusSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

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
            slug__in=["todo", "in_progress", "done"],
        ).order_by("position", "id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["workspace"] = self.get_workspace()
        return context

    def perform_create(self, serializer):
        workspace = self.get_workspace()
        require_workspace_role(
            user=self.request.user,
            workspace=workspace,
            allowed_roles=["owner", "admin"],
        )
        check_workflow_status_limit(workspace)
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
    http_method_names = ["get", "head", "options"]

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

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import WorkspaceInvitation




class WorkspaceMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        from rest_framework.response import Response
        from rest_framework import status as http_status

        workspace = get_object_or_404(
            Workspace,
            pk=workspace_id,
        )

        is_member = WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=request.user,
        ).exists()

        if not is_member:
            return Response(
                {"detail": "You must be a workspace member to view its members."},
                status=http_status.HTTP_403_FORBIDDEN,
            )

        memberships = (
            WorkspaceMembership.objects
            .filter(workspace=workspace)
            .select_related("user")
            .order_by("joined_at")
        )

        from .models import ProjectMembership

        assignments = {}
        project_memberships = (
            ProjectMembership.objects
            .filter(
                user_id__in=[membership.user_id for membership in memberships],
                project__workspace=workspace,
            )
            .select_related("project")
            .order_by("project__name")
        )

        for assignment in project_memberships:
            assignments.setdefault(assignment.user_id, []).append({
                "id": assignment.project_id,
                "name": assignment.project.name,
                "key": assignment.project.key,
            })

        data = [
            {
                "id": membership.id,
                "user_id": membership.user_id,
                "username": membership.user.get_username(),
                "email": membership.user.email,
                "first_name": membership.user.first_name,
                "last_name": membership.user.last_name,
                "role": membership.role,
                "joined_at": membership.joined_at,
                "projects": assignments.get(membership.user_id, []),
                "project_ids": [
                    project["id"]
                    for project in assignments.get(membership.user_id, [])
                ],
            }
            for membership in memberships
        ]

        return Response(data)


class WorkspaceMemberProjectAssignmentsView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def put(self, request, workspace_id, user_id):
        workspace = get_object_or_404(Workspace, pk=workspace_id)

        manager = WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=["owner", "admin"],
        ).exists()

        if not manager:
            return Response(
                {"detail": "Only workspace owners and admins can manage project assignments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_membership = (
            WorkspaceMembership.objects
            .select_for_update()
            .filter(workspace=workspace, user_id=user_id)
            .first()
        )

        if target_membership is None:
            return Response(
                {"detail": "This user is not a member of the workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if target_membership.role != "member":
            return Response(
                {"detail": "Project assignments can only be changed for workspace members."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project_ids = request.data.get("project_ids")

        if not isinstance(project_ids, list):
            return Response(
                {"detail": "project_ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if any(isinstance(value, bool) or not str(value).isdigit() for value in project_ids):
            return Response(
                {"detail": "Every project ID must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project_ids = list(dict.fromkeys(int(value) for value in project_ids))

        valid_projects = Project.objects.filter(
            workspace=workspace,
            id__in=project_ids,
        )

        if valid_projects.count() != len(project_ids):
            return Response(
                {"detail": "One or more projects do not belong to this workspace."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ProjectMembership.objects.filter(
            user_id=user_id,
            project__workspace=workspace,
        ).exclude(project_id__in=project_ids).delete()

        existing_ids = set(
            ProjectMembership.objects.filter(
                user_id=user_id,
                project__workspace=workspace,
                project_id__in=project_ids,
            ).values_list("project_id", flat=True)
        )

        ProjectMembership.objects.bulk_create(
            [
                ProjectMembership(project_id=project_id, user_id=user_id)
                for project_id in project_ids
                if project_id not in existing_ids
            ],
            ignore_conflicts=True,
        )

        return Response({
            "detail": "Project assignments updated.",
            "user_id": user_id,
            "project_ids": project_ids,
        })



class WorkspaceMemberRoleView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, workspace_id, user_id):
        workspace = get_object_or_404(Workspace, pk=workspace_id)

        if not WorkspaceMembership.objects.filter(
            workspace=workspace, user=request.user, role="owner"
        ).exists():
            return Response(
                {"detail": "Only the workspace owner can change member roles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership = WorkspaceMembership.objects.select_for_update().filter(
            workspace=workspace, user_id=user_id
        ).first()

        if membership is None:
            return Response(
                {"detail": "This user is not a member of the workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if membership.role == "owner":
            return Response(
                {"detail": "Workspace owner roles cannot be changed here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_role = request.data.get("role")
        if new_role not in ("admin", "member"):
            return Response(
                {"detail": "Role must be either admin or member."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_role = membership.role
        if new_role != old_role:
            check_role_membership_limit(
                membership.user,
                new_role,
                excluding_workspace_id=workspace.id,
            )
        old_project_ids = set(ProjectMembership.objects.filter(
            user_id=user_id,
            project__workspace=workspace,
        ).values_list("project_id", flat=True))

        if new_role == "member":
            project_ids = request.data.get("project_ids")
            if not isinstance(project_ids, list):
                return Response(
                    {"detail": "project_ids must be a list for workspace members."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if any(
                isinstance(value, bool) or not str(value).isdigit()
                for value in project_ids
            ):
                return Response(
                    {"detail": "Every project ID must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            project_ids = list(dict.fromkeys(int(value) for value in project_ids))
            valid_ids = set(Project.objects.filter(
                workspace=workspace,
                id__in=project_ids,
            ).values_list("id", flat=True))

            if valid_ids != set(project_ids):
                return Response(
                    {"detail": "One or more projects do not belong to this workspace."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            project_ids = []

        new_project_ids = set(project_ids)

        membership.role = new_role
        membership.save(update_fields=["role"])

        # Admins have access to every project; remove obsolete member assignments.
        ProjectMembership.objects.filter(
            user_id=user_id,
            project__workspace=workspace,
        ).delete()

        if new_role == "member":
            ProjectMembership.objects.bulk_create(
                [
                    ProjectMembership(project_id=pid, user_id=user_id)
                    for pid in project_ids
                ],
                ignore_conflicts=True,
            )

        role_changed = old_role != new_role
        projects_changed = old_project_ids != new_project_ids

        if role_changed:
            AuditLog.objects.create(
                workspace=workspace,
                actor=request.user,
                action="workspace.member_role_changed",
                entity_type="WorkspaceMembership",
                entity_id=membership.id,
                details={
                    "user_id": user_id,
                    "member_name": (
                        membership.user.get_full_name()
                        or membership.user.get_username()
                    ),
                    "member_email": membership.user.email,
                    "old_role": old_role,
                    "new_role": new_role,
                },
            )

        added_ids = new_project_ids - old_project_ids
        removed_ids = old_project_ids - new_project_ids

        response_data = {
            "detail": "Member access updated.",
            "user_id": user_id,
            "role": new_role,
            "project_ids": sorted(new_project_ids),
            "email_sent": None,
        }

        if role_changed or projects_changed:
            project_names = {
                project.id: project.name
                for project in Project.objects.filter(
                    workspace=workspace,
                    id__in=added_ids | removed_ids,
                )
            }

            added_projects = [
                project_names[pid] for pid in sorted(added_ids)
                if pid in project_names
            ]
            removed_projects = [
                project_names[pid] for pid in sorted(removed_ids)
                if pid in project_names
            ]

            def send_access_notification():
                try:
                    from .email_service import send_member_access_update_email

                    send_member_access_update_email(
                        recipient=membership.user.email,
                        workspace_name=workspace.name,
                        actor_name=request.user.get_username(),
                        old_role=old_role,
                        new_role=new_role,
                        added_projects=added_projects,
                        removed_projects=removed_projects,
                    )
                    response_data["email_sent"] = True
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception(
                        "Failed to send workspace access notification."
                    )
                    response_data["email_sent"] = False

            transaction.on_commit(send_access_notification)

        return Response(response_data)

        return Response({
            "detail": "Member access updated.",
            "user_id": user_id,
            "role": new_role,
            "project_ids": sorted(new_project_ids),
            "email_sent": email_sent,
        })


class WorkspaceMemberRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, workspace_id, user_id):
        workspace = get_object_or_404(Workspace, pk=workspace_id)

        if not WorkspaceMembership.objects.filter(
            workspace=workspace, user=request.user, role="owner"
        ).exists():
            return Response(
                {"detail": "Only the workspace owner can remove members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership = WorkspaceMembership.objects.select_for_update().filter(
            workspace=workspace, user_id=user_id
        ).first()

        if membership is None:
            return Response(
                {"detail": "This user is not a member of the workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if membership.role == "owner":
            return Response(
                {"detail": "Workspace owners cannot be removed here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        AuditLog.objects.create(
            workspace=workspace,
            actor=request.user,
            action="workspace.member_removed",
            entity_type="WorkspaceMembership",
            entity_id=membership.id,
            details={
                "user_id": user_id,
                "email": membership.user.email,
                "member_email": membership.user.email,
                "member_name": membership.user.get_full_name() or membership.user.get_username(),
                "role": membership.role,
            },
        )

        ProjectMembership.objects.filter(
            user_id=user_id,
            project__workspace=workspace,
        ).delete()

        recipient_email = membership.user.email
        removed_workspace_name = workspace.name
        actor_name = request.user.get_username()

        membership.delete()

        def send_removal_notification():
            try:
                from .email_service import send_member_removed_email

                send_member_removed_email(
                    recipient=recipient_email,
                    workspace_name=removed_workspace_name,
                    actor_name=actor_name,
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "Failed to send workspace member removal email."
                )

        transaction.on_commit(send_removal_notification)

        return Response({"detail": "Member removed from workspace"})


class WorkspaceInvitationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace = get_object_or_404(Workspace, pk=workspace_id)

        allowed = WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=["owner", "admin"],
        ).exists()

        if not allowed:
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        invitations = WorkspaceInvitation.objects.filter(
            workspace=workspace
        ).order_by("-created_at")

        data = [{
            "id": i.id,
            "email": i.email,
            "role": i.role,
            "status": i.status,
            "expires_at": i.expires_at,
            "created_at": i.created_at,
        } for i in invitations]

        return Response(data)

    @transaction.atomic
    def post(self, request, workspace_id):
        workspace = get_object_or_404(
            Workspace.objects.select_for_update(), pk=workspace_id
        )

        allowed = WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=["owner", "admin"],
        ).exists()

        if not allowed:
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        email = str(request.data.get("email", "")).strip().lower()
        role = request.data.get("role", "member")

        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"email": "Enter a valid email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if role not in ["admin", "member"]:
            return Response(
                {"role": "Choose admin or member."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project_ids = request.data.get("project_ids", [])

        if not isinstance(project_ids, list):
            return Response(
                {"project_ids": "Provide a list of project IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if role == "admin" and project_ids:
            return Response(
                {"project_ids": "Project assignments are only used for member invitations."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if role == "member":
            if not project_ids:
                return Response(
                    {"project_ids": "Assign at least one project to a member invitation."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if any(
                isinstance(project_id, bool)
                or not (
                    isinstance(project_id, int)
                    or (isinstance(project_id, str) and project_id.isdigit())
                )
                for project_id in project_ids
            ):
                return Response(
                    {"project_ids": "Project IDs must be positive integers."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            project_ids = list(dict.fromkeys(int(project_id) for project_id in project_ids))

            if any(project_id <= 0 for project_id in project_ids):
                return Response(
                    {"project_ids": "Project IDs must be positive integers."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            valid_project_ids = set(
                Project.objects.filter(
                    workspace=workspace,
                    id__in=project_ids,
                ).values_list("id", flat=True)
            )

            if valid_project_ids != set(project_ids):
                return Response(
                    {"project_ids": "One or more projects do not belong to this workspace."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        User = type(request.user)
        invited_user = User.objects.filter(email__iexact=email).first()

        if invited_user and WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=invited_user,
        ).exists():
            return Response(
                {"detail": "User is already a workspace member."},
                status=status.HTTP_409_CONFLICT,
            )

        existing = WorkspaceInvitation.objects.filter(
            workspace=workspace,
            email__iexact=email,
            status="pending",
        ).first()

        if existing and not existing.is_expired:
            return Response(
                {"detail": "A pending invitation already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        if existing:
            existing.status = "expired"
            existing.save(update_fields=["status"])

        check_invitation_capacity(workspace)
        if invited_user:
            check_invitee_role_capacity(invited_user, role)

        from .email_service import send_workspace_invitation_email

        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email=email,
            role=role,
            invited_by=request.user,
        )

        if role == "member" and project_ids:
            invitation.projects.set(
                Project.objects.filter(workspace=workspace, id__in=project_ids)
            )

        email_sent = False
        try:
            send_workspace_invitation_email(invitation)
            email_sent = True
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Failed to send workspace invitation email."
            )

        return Response({
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role,
            "status": invitation.status,
            "expires_at": invitation.expires_at,
            "project_ids": list(invitation.projects.values_list("id", flat=True)),
            "email_sent": email_sent,
            "detail": (
                "Invitation created and email submitted."
                if email_sent
                else "Invitation created, but email delivery could not be submitted."
            ),
        }, status=status.HTTP_201_CREATED)


class WorkspaceInvitationAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, token):
        invitation = get_object_or_404(
            WorkspaceInvitation.objects.select_for_update(),
            token=token,
        )

        if invitation.status != "pending":
            return Response(
                {"detail": "Invitation is not pending."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invitation.is_expired:
            invitation.status = "expired"
            invitation.save(update_fields=["status"])
            return Response(
                {"detail": "Invitation has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.email.strip().lower() != invitation.email:
            return Response(
                {"detail": "This invitation belongs to another email address."},
                status=status.HTTP_403_FORBIDDEN,
            )

        already_member = WorkspaceMembership.objects.filter(
            workspace=invitation.workspace,
            user=request.user,
        ).exists()

        if not already_member:
            check_member_capacity(invitation.workspace)
            check_invitee_role_capacity(request.user, invitation.role)

        membership, created = WorkspaceMembership.objects.get_or_create(
            workspace=invitation.workspace,
            user=request.user,
            defaults={"role": invitation.role},
        )

        if not created:
            return Response(
                {"detail": "Already a workspace member."},
                status=status.HTTP_409_CONFLICT,
            )

        if membership.role == "member":
            ProjectMembership.objects.bulk_create(
                [
                    ProjectMembership(project=project, user=request.user)
                    for project in invitation.projects.filter(
                        workspace_id=invitation.workspace_id
                    )
                ],
                ignore_conflicts=True,
            )

        invitation.status = "accepted"
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_at"])

        AuditLog.objects.create(
            workspace=invitation.workspace,
            actor=invitation.invited_by or request.user,
            action="workspace.member_added",
            entity_type="WorkspaceMembership",
            entity_id=membership.id,
            details={
                "member_name": request.user.get_full_name() or request.user.get_username(),
                "member_email": request.user.email,
                "role": membership.role,
            },
        )

        return Response({
            "detail": "Invitation accepted.",
            "workspace_id": invitation.workspace_id,
            "workspace_name": invitation.workspace.name,
            "role": membership.role,
            "project_ids": list(
                ProjectMembership.objects.filter(
                    user=request.user,
                    project__workspace=invitation.workspace,
                ).values_list("project_id", flat=True)
            ),
        })


class WorkspaceInvitationRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, invitation_id):
        invitation = get_object_or_404(
            WorkspaceInvitation.objects.select_for_update(),
            pk=invitation_id,
        )

        allowed = WorkspaceMembership.objects.filter(
            workspace=invitation.workspace,
            user=request.user,
            role__in=["owner", "admin"],
        ).exists()

        if not allowed:
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if invitation.status != "pending":
            return Response(
                {"detail": "Only pending invitations can be revoked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation.status = "revoked"
        invitation.save(update_fields=["status"])

        return Response({"detail": "Invitation revoked."})


class WorkspaceDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id):
        workspace = get_object_or_404(
            Workspace.objects.filter(memberships__user=request.user).distinct(),
            pk=workspace_id,
        )
        is_owner = WorkspaceMembership.objects.filter(
            workspace=workspace, user=request.user, role="owner"
        ).exists()
        if not is_owner:
            return Response(
                {"detail": "Only workspace owners can edit workspace details."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        serializer = WorkspaceSerializer(
            workspace, data=request.data, partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def delete(self, request, workspace_id):
        workspace = get_object_or_404(
            Workspace.objects.filter(memberships__user=request.user).distinct(),
            pk=workspace_id,
        )

        is_owner = WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=request.user,
            role="owner",
        ).exists()

        if not is_owner:
            return Response(
                {"detail": "Only workspace owners can delete a workspace."},
                status=http_status.HTTP_403_FORBIDDEN,
            )

        workspace.delete()

        return Response(status=http_status.HTTP_204_NO_CONTENT)
