"""Placeholder authentication views"""
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['POST'])
def login_view(request):
    """Placeholder login view"""
    return Response({"message": "Login view - to be implemented"})


@api_view(['POST'])
def logout_view(request):
    """Placeholder logout view"""
    return Response({"message": "Logout view - to be implemented"})


@api_view(['POST'])
def register_view(request):
    """Placeholder register view"""
    return Response({"message": "Register view - to be implemented"})


@api_view(['GET'])
def current_user_view(request):
    """Placeholder current user view"""
    return Response({"message": "Current user view - to be implemented"})
