from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Message, MessageThread

User = get_user_model()


class MessageThreadSerializer(serializers.ModelSerializer):
    participant_ids = serializers.PrimaryKeyRelatedField(
        source="participants", many=True, queryset=User.objects.all(), write_only=True
    )

    class Meta:
        model = MessageThread
        fields = ["id", "subject", "participant_ids", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    thread = serializers.PrimaryKeyRelatedField(read_only=True)
    thread_id = serializers.PrimaryKeyRelatedField(
        source="thread", queryset=MessageThread.objects.all(), write_only=True
    )
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    recipient = serializers.PrimaryKeyRelatedField(read_only=True)
    recipient_id = serializers.PrimaryKeyRelatedField(
        source="recipient",
        queryset=User.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "thread",
            "thread_id",
            "sender",
            "recipient",
            "recipient_id",
            "content",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "thread", "sender", "recipient", "status", "created_at"]
