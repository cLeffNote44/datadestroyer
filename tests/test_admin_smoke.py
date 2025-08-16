from django.urls import reverse


def test_admin_index_loads(client, superuser):
    client.force_login(superuser)
    resp = client.get(reverse("admin:index"))
    assert resp.status_code == 200
    assert b"Data Destroyer Administration" in resp.content


def test_documents_admin_changelist(client, superuser):
    client.force_login(superuser)
    resp = client.get(reverse("admin:documents_document_changelist"))
    assert resp.status_code == 200


def test_profiles_admin_changelist(client, superuser):
    client.force_login(superuser)
    resp = client.get(reverse("admin:profiles_userprofile_changelist"))
    assert resp.status_code == 200


def test_exposures_admin_changelist(client, superuser):
    client.force_login(superuser)
    resp = client.get(reverse("admin:exposures_deletionrequest_changelist"))
    assert resp.status_code == 200
