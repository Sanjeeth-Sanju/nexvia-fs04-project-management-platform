from rest_framework import serializers

from .models import (
    Workspace,
    Project,
    Board,
    Sprint,
    Issue,
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

        if not workspace.memberships.filter(user=user).exists():
            raise serializers.ValidationError(
                "You do not have access to this workspace."
            )

        return workspace


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ["id", "project", "name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_project(self, project):
        user = self.context["request"].user

        if not project.workspace.memberships.filter(user=user).exists():
            raise serializers.ValidationError(
                "You do not have access to this project."
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

        if not project.workspace.memberships.filter(user=user).exists():
            raise serializers.ValidationError(
                "You do not have access to this project."
            )

        return project


class IssueSerializer(serializers.ModelSerializer):
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