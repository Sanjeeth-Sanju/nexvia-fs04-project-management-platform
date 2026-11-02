from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status

from .models import Workspace, Project, Board, Sprint, Issue
from .serializers import (
    WorkspaceSerializer,
    ProjectSerializer,
    BoardSerializer,
    SprintSerializer,
    IssueSerializer,
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

        new_status = request.data.get("status")
        new_position = request.data.get("position")

        valid_statuses = {
            choice[0] for choice in Issue.STATUS_CHOICES
        }

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

        return Response(
            {
                "id": issue.id,
                "status": issue.status,
                "position": issue.position,
            },
            status=http_status.HTTP_200_OK,
        )
