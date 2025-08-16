"""
URL configuration for destroyer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from documents.views import DocumentViewSet
from forum.views import PostViewSet, TopicViewSet
from messaging.views import MessageThreadViewSet, MessageViewSet

from .views import health, ready

# Brand the Django admin site
admin.site.site_header = "Data Destroyer Administration"
admin.site.site_title = "Data Destroyer Admin"
admin.site.index_title = "Admin Dashboard"

router = DefaultRouter()
router.register(r"documents", DocumentViewSet, basename="documents")
router.register(r"forum/topics", TopicViewSet, basename="forum-topics")
router.register(r"forum/posts", PostViewSet, basename="forum-posts")
router.register(r"messaging/threads", MessageThreadViewSet, basename="messaging-threads")
router.register(r"messaging/messages", MessageViewSet, basename="messaging-messages")

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health and readiness endpoints
    path("health/", health, name="health"),
    path("ready/", ready, name="ready"),
    # API routes
    path("api/", include(router.urls)),
    # API schema and docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

# Include Django Debug Toolbar URLs in development
if settings.DEBUG:
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    except Exception:
        # If debug_toolbar isn't installed, skip including its URLs
        pass
        pass
