import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def api_user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="apiuser", email="api@example.com", password="pass1234"
    )


def test_api_documents_requires_auth(client):
    resp = client.get("/api/documents/")
    assert resp.status_code in (401, 403)


def test_api_documents_list_for_user(client, api_user):
    client.force_login(api_user)
    resp = client.get("/api/documents/")
    assert resp.status_code == 200


def test_api_document_update_owner_only(client, db):
    # Create two users
    from django.contrib.auth import get_user_model

    from documents.models import Document, DocumentCategory

    User = get_user_model()
    owner = User.objects.create_user(username="owner", password="pass1234")
    other = User.objects.create_user(username="other", password="pass1234")

    # Minimal document without actual file upload: populate required metadata fields
    category = DocumentCategory.objects.create(name="Cat", slug="cat")
    doc = Document.objects.create(
        owner=owner,
        category=category,
        title="Doc1",
        description="",
        file_size=0,
        file_hash="x" * 64,
        mime_type="text/plain",
        is_encrypted=False,
    )

    # Other user cannot update
    client.force_login(other)
    resp = client.patch(
        f"/api/documents/{doc.id}/", data={"title": "X"}, content_type="application/json"
    )
    assert resp.status_code in (403, 404)

    # Owner can update
    client.force_login(owner)
    resp = client.patch(
        f"/api/documents/{doc.id}/", data={"title": "New"}, content_type="application/json"
    )
    assert resp.status_code in (200, 202)
    assert resp.json()["title"] == "New"


def test_api_forum_topics(client, api_user):
    client.force_login(api_user)
    # Create a topic
    payload = {"title": "Hello", "category_id": None}
    # Ensure there is at least one category through seed or create a quick one via ORM
    from forum.models import ForumCategory

    cat, _ = ForumCategory.objects.get_or_create(name="General", slug="general")
    payload["category_id"] = cat.id
    create = client.post("/api/forum/topics/", data=payload)
    assert create.status_code in (201, 200)
    topic_id = create.json()["id"]
    # Update topic (author)
    upd = client.patch(
        f"/api/forum/topics/{topic_id}/",
        data={"title": "Hello World"},
        content_type="application/json",
    )
    assert upd.status_code in (200, 202)
    # Create a post
    post_create = client.post(
        "/api/forum/posts/",
        data={"topic_id": topic_id, "content": "First!"},
    )
    assert post_create.status_code in (201, 200)
    # List
    resp = client.get("/api/forum/topics/")
    assert resp.status_code == 200


def test_api_messaging_threads(client, api_user):
    client.force_login(api_user)
    # Create a thread with self as participant
    payload = {"subject": "Chat", "participant_ids": [api_user.id]}
    create = client.post("/api/messaging/threads/", data=payload)
    assert create.status_code in (201, 200)
    thread_id = create.json()["id"]
    # Send a message in that thread
    msg = client.post(
        "/api/messaging/messages/",
        data={"thread_id": thread_id, "content": "Hello"},
    )
    assert msg.status_code in (201, 200)
    # Ensure non-participant cannot post
    from django.contrib.auth import get_user_model

    User = get_user_model()
    stranger = User.objects.create_user(username="stranger", password="pass1234")
    client.force_login(stranger)
    denied = client.post(
        "/api/messaging/messages/",
        data={"thread_id": thread_id, "content": "I should not post"},
    )
    assert denied.status_code in (403, 404)
    resp = client.get("/api/messaging/threads/")
    assert resp.status_code == 200
