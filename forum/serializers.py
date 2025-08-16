from rest_framework import serializers

from .models import ForumCategory, Post, Topic


class ForumCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ForumCategory
        fields = ["id", "name", "slug"]


class TopicSerializer(serializers.ModelSerializer):
    category = ForumCategorySerializer(read_only=True)

    class Meta:
        model = Topic
        fields = ["id", "title", "category", "status", "created_at", "updated_at"]
        read_only_fields = fields


class PostSerializer(serializers.ModelSerializer):
    topic = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Post
        fields = ["id", "topic", "content", "status", "created_at", "updated_at"]
        read_only_fields = fields
