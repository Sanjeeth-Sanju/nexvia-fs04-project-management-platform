from django.contrib import admin
from .models import (
    Workspace,
    WorkspaceMembership,
    Project,
    Board,
    Sprint,
    Issue,
)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "role", "joined_at")
    list_filter = ("role", "workspace")
    search_fields = ("user__username", "workspace__name")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "workspace", "created_at")
    list_filter = ("workspace",)
    search_fields = ("name", "key", "workspace__name")


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "created_at")
    list_filter = ("project",)
    search_fields = ("name", "project__name")


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "status", "start_date", "end_date")
    list_filter = ("status", "project")
    search_fields = ("name", "project__name")


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "board",
        "status",
        "priority",
        "assignee",
    )
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "project__name", "project__key")