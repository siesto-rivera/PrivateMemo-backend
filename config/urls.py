from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("memos.urls")),
    path(
        "privacy/",
        TemplateView.as_view(template_name="legal/privacy.html"),
        name="privacy",
    ),
]
