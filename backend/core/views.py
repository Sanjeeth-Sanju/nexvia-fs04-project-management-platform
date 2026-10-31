from rest_framework import generics
from .models import Workspace
from .serializers import WorkspaceSerializer


class WorkspaceListView(generics.ListAPIView):
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer