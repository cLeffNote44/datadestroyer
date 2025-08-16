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


def test_api_forum_topics(client, api_user):
    client.force_login(api_user)
    resp = client.get("/api/forum/topics/")
    assert resp.status_code == 200


def test_api_messaging_threads(client, api_user):
    client.force_login(api_user)
    resp = client.get("/api/messaging/threads/")
    assert resp.status_code == 200
