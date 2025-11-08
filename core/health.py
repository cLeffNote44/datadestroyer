"""
Health check endpoints for monitoring and load balancing
"""
import time
from typing import Dict

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone


def health_check(request) -> JsonResponse:
    """
    Comprehensive health check endpoint

    Returns:
        200 OK if all services are healthy
        503 Service Unavailable if any critical service is down
    """
    start_time = time.time()
    status = {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "checks": {},
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except Exception as e:
        status["status"] = "unhealthy"
        status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }

    # Check cache (Redis)
    try:
        cache_key = "health_check_test"
        cache_value = "ok"
        cache.set(cache_key, cache_value, timeout=10)
        cached = cache.get(cache_key)

        if cached == cache_value:
            status["checks"]["cache"] = {
                "status": "healthy",
                "message": "Cache read/write successful",
            }
        else:
            status["checks"]["cache"] = {
                "status": "degraded",
                "message": "Cache read/write verification failed",
            }
    except Exception as e:
        status["checks"]["cache"] = {
            "status": "degraded",
            "message": f"Cache error: {str(e)}",
        }

    # Check disk space (if media files are stored locally)
    try:
        import shutil

        if hasattr(settings, "MEDIA_ROOT"):
            disk_usage = shutil.disk_usage(settings.MEDIA_ROOT)
            free_percent = (disk_usage.free / disk_usage.total) * 100

            if free_percent < 10:
                status["checks"]["disk"] = {
                    "status": "warning",
                    "message": f"Low disk space: {free_percent:.1f}% free",
                    "free_percent": round(free_percent, 2),
                }
            else:
                status["checks"]["disk"] = {
                    "status": "healthy",
                    "message": f"Disk space OK: {free_percent:.1f}% free",
                    "free_percent": round(free_percent, 2),
                }
    except Exception as e:
        status["checks"]["disk"] = {
            "status": "unknown",
            "message": f"Could not check disk space: {str(e)}",
        }

    # Calculate response time
    response_time_ms = (time.time() - start_time) * 1000
    status["response_time_ms"] = round(response_time_ms, 2)

    # Determine HTTP status code
    http_status = 200
    if status["status"] == "unhealthy":
        http_status = 503
    elif any(
        check.get("status") == "warning" for check in status["checks"].values()
    ):
        status["status"] = "degraded"

    return JsonResponse(status, status=http_status)


def liveness_check(request) -> JsonResponse:
    """
    Kubernetes liveness probe - checks if the application is running

    Returns:
        200 OK if the application process is running
    """
    return JsonResponse(
        {
            "status": "alive",
            "timestamp": timezone.now().isoformat(),
        }
    )


def readiness_check(request) -> JsonResponse:
    """
    Kubernetes readiness probe - checks if the application is ready to serve traffic

    Returns:
        200 OK if the application is ready
        503 Service Unavailable if not ready
    """
    status = {"status": "ready", "timestamp": timezone.now().isoformat(), "checks": {}}

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["checks"]["database"] = "ready"
    except Exception as e:
        status["status"] = "not_ready"
        status["checks"]["database"] = f"not_ready: {str(e)}"
        return JsonResponse(status, status=503)

    # Check cache
    try:
        cache.get("readiness_check")
        status["checks"]["cache"] = "ready"
    except Exception as e:
        status["checks"]["cache"] = f"degraded: {str(e)}"

    return JsonResponse(status, status=200)


def metrics_endpoint(request) -> JsonResponse:
    """
    Application metrics in Prometheus-compatible format

    Note: For production, use django-prometheus middleware instead
    This is a simple fallback endpoint
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        metrics = {
            "users_total": User.objects.count(),
            "users_active_last_30_days": User.objects.filter(
                last_login__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
        }

        # Add application-specific metrics
        try:
            from discovery.models import DataAsset, DiscoveryJob

            metrics["data_assets_total"] = DataAsset.objects.count()
            metrics["discovery_jobs_total"] = DiscoveryJob.objects.count()
            metrics["discovery_jobs_running"] = DiscoveryJob.objects.filter(
                status="running"
            ).count()
        except ImportError:
            pass

        try:
            from moderation.models import ContentScan, PolicyViolation

            metrics["content_scans_total"] = ContentScan.objects.count()
            metrics["policy_violations_total"] = PolicyViolation.objects.count()
            metrics["policy_violations_pending"] = PolicyViolation.objects.filter(
                status="pending"
            ).count()
        except ImportError:
            pass

        return JsonResponse(
            {
                "status": "ok",
                "timestamp": timezone.now().isoformat(),
                "metrics": metrics,
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "status": "error",
                "timestamp": timezone.now().isoformat(),
                "error": str(e),
            },
            status=500,
        )
