from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),

    path("dashboard/", include("dashboard.urls")),

    path("", include("pages.urls")),
    path("", include("bookings.urls")),
]