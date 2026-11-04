from django.urls import path

from .views import (
    WorkspaceListView,
    ProjectListCreateView,
    BoardListCreateView,
    SprintListCreateView,
    IssueListCreateView,
    IssueDetailView,
    IssueMoveView,
    IssueCommentListCreateView,
    IssueAttachmentListCreateView,
    IssueAttachmentDetailView,
    AuditLogListView,
    WorkflowStatusListCreateView,
    WorkflowStatusDetailView,
    WorkflowStatusReorderView,
)

urlpatterns = [
    path("workspaces/", WorkspaceListView.as_view(), name="workspace-list"),
    path("projects/", ProjectListCreateView.as_view(), name="project-list-create"),
    path("boards/", BoardListCreateView.as_view(), name="board-list-create"),
    path("sprints/", SprintListCreateView.as_view(), name="sprint-list-create"),
    path("issues/", IssueListCreateView.as_view(), name="issue-list-create"),
    path("issues/<int:pk>/", IssueDetailView.as_view(), name="issue-detail"),
    path("issues/<int:pk>/move/", IssueMoveView.as_view(), name="issue-move"),
    path("issues/<int:issue_pk>/comments/", IssueCommentListCreateView.as_view(), name="issue-comments"),
    path("issues/<int:issue_pk>/attachments/", IssueAttachmentListCreateView.as_view(), name="issue-attachments"),
    path("workspaces/<int:workspace_pk>/audit-logs/", AuditLogListView.as_view(), name="audit-log-list"),
    path("attachments/<int:pk>/", IssueAttachmentDetailView.as_view(), name="issue-attachment-detail"),
    path("workspaces/<int:workspace_pk>/workflow-statuses/", WorkflowStatusListCreateView.as_view(), name="workflow-status-list-create"),
    path("workspaces/<int:workspace_pk>/workflow-statuses/<int:pk>/", WorkflowStatusDetailView.as_view(), name="workflow-status-detail"),
    path("workspaces/<int:workspace_pk>/workflow-statuses/reorder/",WorkflowStatusReorderView.as_view(),name="workflow-status-reorder"),
]