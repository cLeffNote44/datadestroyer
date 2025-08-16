from rest_framework import serializers

from .models import Document, DocumentCategory


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = ["id", "name", "slug", "is_sensitive"]


class DocumentSerializer(serializers.ModelSerializer):
    category = DocumentCategorySerializer(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "description",
            "category",
            "file_size",
            "mime_type",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
