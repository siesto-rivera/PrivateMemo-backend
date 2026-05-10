from django.urls import path

from .views import (
    MeView,
    SignupView,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)


urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", ThrottledTokenObtainPairView.as_view(), name="login"),
    path("refresh/", ThrottledTokenRefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
]
