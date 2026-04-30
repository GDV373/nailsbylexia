from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    list_display = (
        "email",
        "username",
        "phone",
        "is_staff",
        "is_superuser",
        "is_active",
    )

    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
    )

    search_fields = (
        "email",
        "username",
        "phone",
    )

    ordering = ("email",)

    fieldsets = UserAdmin.fieldsets + (
        ("Extra Details", {
            "fields": ("phone",)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra Details", {
            "fields": ("email", "phone")
        }),
    )