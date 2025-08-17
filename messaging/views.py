from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import Message, MessageThread
from .serializers import MessageSerializer, MessageThreadSerializer


class IsParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Object-level: user must be in participants
        if hasattr(obj, "participants"):
            return obj.participants.filter(id=request.user.id).exists()
        # Message objects have a 'thread' FK
        if hasattr(obj, "thread_id") or hasattr(obj, "thread"):
            return obj.thread.participants.filter(id=request.user.id).exists()
        return False


class MessageThreadViewSet(viewsets.ModelViewSet):
    serializer_class = MessageThreadSerializer
    permission_classes = [permissions.IsAuthenticated, IsParticipant]

    def get_queryset(self):
        return (
            MessageThread.objects.filter(participants=self.request.user)
            .order_by("-updated_at")
            .distinct()
        )

    def perform_create(self, serializer):
        thread = serializer.save(created_by=self.request.user)
        # Ensure creator is in participants
        thread.participants.add(self.request.user)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsParticipant]

    def get_queryset(self):
        return (
            Message.objects.filter(thread__participants=self.request.user)
            .select_related("thread", "sender", "recipient")
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        thread = serializer.validated_data["thread"]
        # Ensure the user is a participant of the thread
        if not thread.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied("Not a participant of this thread")
        serializer.save(sender=self.request.user)
