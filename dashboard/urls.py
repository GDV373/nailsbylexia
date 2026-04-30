from django.urls import path
from . import views

urlpatterns = [
    path("availability/", views.availability_builder, name="availability_builder"),

    path("users/", views.admin_users, name="admin_users"),
    path("users/<int:user_id>/toggle-staff/", views.toggle_user_staff, name="toggle_user_staff"),
    path("users/<int:user_id>/toggle-active/", views.toggle_user_active, name="toggle_user_active"),
    path("users/<int:user_id>/toggle-superuser/", views.toggle_user_superuser, name="toggle_user_superuser"),
]