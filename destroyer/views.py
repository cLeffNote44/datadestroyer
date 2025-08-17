from django.http import HttpResponse, JsonResponse


def health(request):
    return JsonResponse({"status": "ok"})


def ready(request):
    # In a more advanced setup, check DB and cache connections here
    return JsonResponse({"status": "ready"})


def home(request):
    return HttpResponse("It works")
