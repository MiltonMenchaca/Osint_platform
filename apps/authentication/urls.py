from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from . import views

router = DefaultRouter()
# router.register(r'users', views.UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("user/", views.current_user, name="current_user"),
    path("user/stats/", views.user_stats, name="user_stats"),
    path("user/activity/", views.user_activity, name="user_activity"),
    path("user/permissions/", views.check_permissions, name="check_permissions"),
    # Add custom URL patterns here
]
