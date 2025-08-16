import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse

from documents.models import Document, DocumentAccessLog, DocumentCategory
from forum.models import ForumCategory, Post, Topic
from messaging.models import MessageThread, ThreadParticipant


@pytest.fixture
def owner_user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="owner_user", email="owner@example.com", password="pass1234!"
    )


@pytest.fixture
def sample_document(db, owner_user, tmp_path):
    # Create category
    cat = DocumentCategory.objects.create(name="Reports", slug="reports")
    # Create a small in-memory file
    content = ContentFile(b"hello world", name="hello.txt")
    doc = Document.objects.create(
        owner=owner_user,
        category=cat,
        title="Test Doc",
        description="",
        file=content,
        file_size=11,
        file_hash="",  # let model compute if needed
        mime_type="text/plain",
        is_encrypted=False,
        status="active",
    )
    return doc


@pytest.fixture
def sample_access_log(db, sample_document, owner_user):
    return DocumentAccessLog.objects.create(
        document=sample_document,
        user=owner_user,
        action="view",
        success=True,
        ip_address="127.0.0.1",
        user_agent="pytest",
        session_key=str(uuid.uuid4()),
    )


@pytest.fixture
def sample_topic(db, owner_user):
    cat = ForumCategory.objects.create(name="General", slug="general")
    topic = Topic.objects.create(category=cat, author=owner_user, title="Welcome")
    Post.objects.create(topic=topic, author=owner_user, content="First post")
    return topic


@pytest.fixture
def sample_thread(db, owner_user):
    thread = MessageThread.objects.create(subject="Chat", created_by=owner_user)
    ThreadParticipant.objects.create(thread=thread, user=owner_user)
    return thread


def test_document_change_has_accesslog_inline_readonly(
    client, superuser, sample_document, sample_access_log
):
    client.force_login(superuser)
    url = reverse("admin:documents_document_change", args=[sample_document.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    # Inline management form present using related_name 'access_logs'
    assert b"access_logs-TOTAL_FORMS" in resp.content
    # No delete checkbox for inline rows
    assert b"access_logs-0-DELETE" not in resp.content


def test_accesslog_changelist_has_no_bulk_delete_action(client, superuser, sample_access_log):
    client.force_login(superuser)
    url = reverse("admin:documents_documentaccesslog_changelist")
    resp = client.get(url)
    assert resp.status_code == 200
    # Built-in delete_selected action should be removed
    assert b"delete_selected" not in resp.content


def test_topic_change_has_posts_inline_readonly(client, superuser, sample_topic):
    client.force_login(superuser)
    url = reverse("admin:forum_topic_change", args=[sample_topic.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    # Inline management form present using related_name 'posts'
    assert b"posts-TOTAL_FORMS" in resp.content
    # Read-only inline: no delete checkbox
    assert b"posts-0-DELETE" not in resp.content


def test_thread_change_has_participants_inline(client, superuser, sample_thread):
    client.force_login(superuser)
    url = reverse("admin:messaging_messagethread_change", args=[sample_thread.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    # Inline management form present; related_name is 'thread_participants'
    assert b"thread_participants-TOTAL_FORMS" in resp.content
