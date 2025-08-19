from rest_framework import permissions, viewsets

from .models import Document
from .serializers import DocumentSerializer


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(obj, "owner_id", None) == request.user.id


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        # Handle schema introspection with fake queryset
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()
        return Document.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
