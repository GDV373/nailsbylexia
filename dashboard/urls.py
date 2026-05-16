from django.urls import path
from . import views

urlpatterns = [
    path("availability/", views.availability_builder, name="availability_builder"),
    path("availability/<int:slot_id>/edit/", views.edit_availability, name="edit_availability"),
    path("availability/<int:slot_id>/delete/", views.delete_availability, name="delete_availability"),

    path("services/", views.services_manager, name="services_manager"),
    path("services/add/", views.add_service, name="add_service"),
    path("services/<int:service_id>/edit/", views.edit_service, name="edit_service"),
    path("services/<int:service_id>/delete/", views.delete_service, name="delete_service"),
    path("services/seed-defaults/", views.seed_default_services, name="seed_default_services"),

    path("users/", views.admin_users, name="admin_users"),
    path("users/<int:user_id>/toggle-staff/", views.toggle_user_staff, name="toggle_user_staff"),
    path("users/<int:user_id>/toggle-active/", views.toggle_user_active, name="toggle_user_active"),
    path("users/<int:user_id>/toggle-superuser/", views.toggle_user_superuser, name="toggle_user_superuser"),

    path("bookings/", views.admin_bookings, name="admin_bookings"),
    path("bookings/<int:booking_id>/complete/", views.complete_booking, name="complete_booking"),
    path("bookings/<int:booking_id>/cancel/", views.admin_cancel_booking, name="admin_cancel_booking"),
    path("bookings/<int:booking_id>/reschedule/", views.admin_reschedule_booking, name="admin_reschedule_booking"),
]
