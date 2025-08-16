import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone

from documents.models import Document, DocumentCategory, DocumentStatus
from forum.models import ForumCategory, Post, PostStatus, Topic
from messaging.models import Message, MessageStatus, MessageThread


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(username="u1", email="u1@example.com", password="p")


@pytest.fixture
def user2(db):
    User = get_user_model()
    return User.objects.create_user(username="u2", email="u2@example.com", password="p")


def test_document_schedule_and_mark_deleted(db, user):
    cat = DocumentCategory.objects.create(name="Cat1", slug="cat1")
    content = ContentFile(b"hello", name="hello.txt")
    doc = Document.objects.create(
        owner=user,
        category=cat,
        title="Doc1",
        description="",
        file=content,
        file_size=5,
        file_hash="",
        mime_type="text/plain",
    )

    # schedule deletion uses default category retention when days not provided
    before = timezone.now()
    doc.schedule_deletion()  # uses category.default_retention_days (default 90)
    assert doc.status == DocumentStatus.SCHEDULED_DELETE
    assert doc.retention_date is not None and doc.retention_date > before

    # mark as deleted
    doc.mark_as_deleted()
    assert doc.status == DocumentStatus.DELETED
    assert doc.deletion_date is not None


def test_forum_schedule_methods(db, user):
    fc = ForumCategory.objects.create(name="General", slug="general")
    topic = Topic.objects.create(category=fc, author=user, title="Welcome")
    topic.schedule_deletion(days=10)
    assert topic.retention_date is not None

    post = Post.objects.create(topic=topic, author=user, content="hi")
    post.schedule_deletion(days=5)
    assert post.status == PostStatus.SCHEDULED_DELETE
    assert post.retention_date is not None

    post.mark_as_deleted()
    assert post.status == PostStatus.DELETED
    assert post.deletion_date is not None


def test_messaging_schedule_methods(db, user, user2):
    thread = MessageThread.objects.create(subject="Chat", created_by=user)
    msg = Message.objects.create(
        thread=thread,
        sender=user,
        recipient=user2,
        content="hello",
    )
    msg.schedule_deletion(days=3)
    assert msg.status == MessageStatus.SCHEDULED_DELETE
    assert msg.retention_date is not None

    msg.mark_as_deleted()
    assert msg.status == MessageStatus.DELETED
    assert msg.deletion_date is not None
