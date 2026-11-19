from django.utils.text import slugify
from rest_framework import serializers
from .permissions import require_workspace_role

from .models import (
    Workspace,
    Project,
    ProjectMembership,
    Board,
    Sprint,
    Issue,
    IssueComment,
    IssueAttachment,
    AuditLog,
    WorkflowStatus,
)


class WorkspaceSerializer(serializers.ModelSerializer):
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "created_at", "current_user_role"]
        read_only_fields = ["id", "slug", "created_at", "current_user_role"]

    def validate_name(self, value):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            owned_workspaces = Workspace.objects.filter(
                memberships__user=request.user,
                memberships__role="owner",
                name__iexact=value.strip(),
            )

            if self.instance is not None:
                owned_workspaces = owned_workspaces.exclude(
                    pk=self.instance.pk
                )

            if owned_workspaces.exists():
                raise serializers.ValidationError(
                    "You already own a workspace with this name. "
                    "Choose a different name."
                )

        return value.strip()

    def get_current_user_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        membership = obj.memberships.filter(user=request.user).only("role").first()
        return membership.role if membership else None

    def create(self, validated_data):
        name = validated_data["name"]
        base_slug = slugify(name)

        if not base_slug:
            raise serializers.ValidationError({
                "name": "Enter a name containing letters or numbers."
            })

        slug = base_slug
        counter = 2

        while Workspace.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return Workspace.objects.create(
            name=name,
            slug=slug,
        )


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id",
            "workspace",
            "name",
            "key",
            "description",
            "status",
            "completed_at",
            "completed_by",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "completed_at",
            "completed_by",
            "created_at",
        ]

    def validate_workspace(self, workspace):
        user = self.context["request"].user

        require_workspace_role(
            user=user,
            workspace=workspace,
            allowed_roles=["owner", "admin"],
        )

        return workspace


class ProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["name", "key", "description"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Project name cannot be empty.")
        return value

    def validate_key(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Project key cannot be empty.")
        if len(value) > 10:
            raise serializers.ValidationError("Project key must be 10 characters or fewer.")
        queryset = Project.objects.filter(
            workspace=self.instance.workspace,
            key__iexact=value,
        ).exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "A project with this key already exists in the workspace."
            )
        return value


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

        if self.instance and project.id != self.instance.project_id:
            raise serializers.ValidationError({
                "project": "A sprint cannot be moved to another project."
            })

        return project

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot be earlier than the start date."
            })

        return attrs


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

        has_workspace_admin_access = project.workspace.memberships.filter(
            user=user,
            role__in=["owner", "admin"],
        ).exists()

        has_project_assignment = ProjectMembership.objects.filter(
            project=project,
            user=user,
        ).exists()

        if not has_workspace_admin_access and not has_project_assignment:
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