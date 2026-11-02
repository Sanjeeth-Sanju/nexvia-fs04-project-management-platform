from django.urls import path

from .views import (
    WorkspaceListView,
    ProjectListCreateView,
    BoardListCreateView,
    SprintListCreateView,
    IssueListCreateView,
    IssueDetailView,
    IssueMoveView,
)

urlpatterns = [
    path("workspaces/", WorkspaceListView.as_view(), name="workspace-list"),
    path("projects/", ProjectListCreateView.as_view(), name="project-list-create"),
    path("boards/", BoardListCreateView.as_view(), name="board-list-create"),
    path("sprints/", SprintListCreateView.as_view(), name="sprint-list-create"),
    path("issues/", IssueListCreateView.as_view(), name="issue-list-create"),
    path("issues/<int:pk>/", IssueDetailView.as_view(), name="issue-detail"),
    path("issues/<int:pk>/move/", IssueMoveView.as_view(), name="issue-move"),
]