from rest_framework import serializers
from .permissions import require_workspace_role

from .models import (
    Workspace,
    Project,
    Board,
    Sprint,
    Issue,
    IssueComment,
    IssueAttachment,
    AuditLog,
    WorkflowStatus,
)


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "created_at"]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id",
            "workspace",
            "name",
            "key",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_workspace(self, workspace):
        user = self.context["request"].user

        require_workspace_role(
            user=user,
            workspace=workspace,
            allowed_roles=["owner", "admin"],
        )

        return workspace


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ["id", "project", "name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_project(self, project):
        user = self.context["request"].user

        require_workspace_role(
            user=user,
            workspace=project.workspace,
            allowed_roles=["owner", "admin"],
        )

        return project


class SprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sprint
        fields = [
            "id",
            "project",
            "name",
            "goal",
            "start_date",
            "end_date",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_project(self, project):
        user = self.context["request"].user

        require_workspace_role(
            user=user,
            workspace=project.workspace,
            allowed_roles=["owner", "admin"],
        )

        return project


class IssueSerializer(serializers.ModelSerializer):
    status = serializers.CharField(max_length=20, required=False)
    class Meta:
        model = Issue
        fields = [
            "id",
            "project",
            "board",
            "sprint",
            "title",
            "description",
            "issue_type",
            "priority",
            "status",
            "assignee",
            "position",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        user = self.context["request"].user

        project = attrs.get(
            "project",
            getattr(self.instance, "project", None),
        )
        board = attrs.get(
            "board",
            getattr(self.instance, "board", None),
        )
        sprint = attrs.get(
            "sprint",
            getattr(self.instance, "sprint", None),
        )
        assignee = attrs.get(
            "assignee",
            getattr(self.instance, "assignee", None),
        )

        if project is None:
            raise serializers.ValidationError(
                {"project": "A project is required."}
            )

        if not project.workspace.memberships.filter(user=user).exists():
            raise serializers.ValidationError(
                {"project": "You do not have access to this project."}
            )


        status_value = attrs.get(
            "status",
            getattr(self.instance, "status", "todo"),
        )

        if not WorkflowStatus.objects.filter(
            workspace=project.workspace,
            slug=status_value,
        ).exists():
            raise serializers.ValidationError(
                {"status": "Invalid issue status for this workspace."}
            )


        if board and board.project_id != project.id:
            raise serializers.ValidationError(
                {"board": "The board must belong to the selected project."}
            )

        if sprint and sprint.project_id != project.id:
            raise serializers.ValidationError(
                {"sprint": "The sprint must belong to the selected project."}
            )

        if assignee and not project.workspace.memberships.filter(
            user=assignee
        ).exists():
            raise serializers.ValidationError(
                {"assignee": "The assignee must be a workspace member."}
            )

        return attrs
class IssueCommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = IssueComment
        fields = [
            "id",
            "issue",
            "author",
            "body",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author",
            "issue",
            "created_at",
            "updated_at",
        ]        

class IssueAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = IssueAttachment
        fields = [
            "id",
            "issue",
            "uploaded_by",
            "file",
            "filename",
            "uploaded_at",
        ]
        read_only_fields = [
            "id",
            "issue",
            "uploaded_by",
            "filename",
            "uploaded_at",
        ]        

class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "workspace",
            "actor",
            "action",
            "entity_type",
            "entity_id",
            "details",
            "created_at",
        ]
        read_only_fields = fields        

class WorkflowStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStatus
        fields = [
            "id",
            "workspace",
            "name",
            "slug",
            "position",
            "is_default",
            "is_completed",
        ]
        read_only_fields = ["id", "workspace", "is_default"]

    def validate(self, attrs):
        request = self.context["request"]
        workspace = self.context["workspace"]

        require_workspace_role(
            user=request.user,
            workspace=workspace,
            allowed_roles=["owner", "admin"],
        )

        # Creation: role validation is sufficient.
        if self.instance is None:
            return attrs

        status = self.instance

        # Built-in default statuses keep their defining fields.
        if status.is_default:
            protected_fields = ["slug", "is_completed"]

            for field in protected_fields:
                if field in attrs and attrs[field] != getattr(status, field):
                    raise serializers.ValidationError({
                        field: "This field cannot be changed for a default workflow status."
                    })

        # A slug change must not invalidate existing issues.
        new_slug = attrs.get("slug", status.slug)

        if new_slug != status.slug:
            from .models import Issue

            if Issue.objects.filter(
                project__workspace=workspace,
                status=status.slug,
            ).exists():
                raise serializers.ValidationError({
                    "slug": (
                        "This status is used by existing issues and its slug "
                        "cannot be changed."
                    )
                })

        return attrs
   
        
class WorkflowStatusReorderSerializer(serializers.Serializer):
    status_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate_status_ids(self, status_ids):
        if len(status_ids) != len(set(status_ids)):
            raise serializers.ValidationError(
                "Each workflow status ID must appear only once."
            )

        workspace = self.context["workspace"]

        existing_ids = set(
            WorkflowStatus.objects.filter(workspace=workspace)
            .values_list("id", flat=True)
        )

        if set(status_ids) != existing_ids:
            raise serializers.ValidationError(
                "Provide every workflow status ID in this workspace exactly once."
            )

        return status_ids        