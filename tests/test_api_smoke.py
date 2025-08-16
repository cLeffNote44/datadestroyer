from django.urls import reverse


def test_health_endpoint(client):
    resp = client.get(reverse("health"))
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_ready_endpoint(client):
    resp = client.get(reverse("ready"))
    assert resp.status_code == 200
    assert resp.json().get("status") == "ready"


def test_api_schema(client):
    resp = client.get(reverse("schema"))
    assert resp.status_code == 200
    assert "openapi" in resp.content.decode("utf-8").lower()


def test_api_docs(client):
    resp = client.get(reverse("swagger-ui"))
    assert resp.status_code == 200
