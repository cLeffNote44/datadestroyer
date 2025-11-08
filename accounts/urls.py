from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import current_user_view, login_view, logout_view, register_view

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('me/', current_user_view, name='current_user'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

app_name = 'accounts'
