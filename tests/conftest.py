import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def superuser(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin_test",
        email="admin_test@example.com",
        password="admin_test_password",
    )
