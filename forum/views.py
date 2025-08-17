from rest_framework import permissions, viewsets

from .models import Post, Topic
from .serializers import PostSerializer, TopicSerializer


class IsAuthor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(obj, "author_id", None) == request.user.id


class TopicViewSet(viewsets.ModelViewSet):
    serializer_class = TopicSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthor]

    def get_queryset(self):
        return Topic.objects.select_related("category", "author").order_by("-updated_at")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthor]

    def get_queryset(self):
        return Post.objects.select_related("topic", "author").order_by("created_at")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
