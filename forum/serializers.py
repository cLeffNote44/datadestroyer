from rest_framework import serializers

from .models import ForumCategory, Post, Topic


class ForumCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ForumCategory
        fields = ["id", "name", "slug"]


class TopicSerializer(serializers.ModelSerializer):
    category = ForumCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=ForumCategory.objects.all(), write_only=True
    )

    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "category",
            "category_id",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "category", "status", "created_at", "updated_at"]


class PostSerializer(serializers.ModelSerializer):
    topic = serializers.PrimaryKeyRelatedField(read_only=True)
    topic_id = serializers.PrimaryKeyRelatedField(
        source="topic", queryset=Topic.objects.all(), write_only=True
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "topic",
            "topic_id",
            "content",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "topic", "status", "created_at", "updated_at"]
