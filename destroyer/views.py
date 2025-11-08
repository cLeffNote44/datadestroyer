from django.http import HttpResponse

# Import comprehensive health check functions
from core.health import health_check, liveness_check, readiness_check

# Use the comprehensive health check as default
health = health_check
ready = readiness_check


def home(request):
    return HttpResponse("Data Destroyer API - Use /api/docs/ for API documentation")
