from rest_framework import permissions, viewsets

from .models import Message, MessageThread
from .serializers import MessageSerializer, MessageThreadSerializer


class MessageThreadViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            MessageThread.objects.filter(participants=self.request.user)
            .order_by("-updated_at")
            .distinct()
        )


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Message.objects.filter(thread__participants=self.request.user)
            .select_related("thread", "sender", "recipient")
            .order_by("created_at")
        )
