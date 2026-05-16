from django.urls import path
from . import views

urlpatterns = [
    path("book/", views.create_booking, name="create_booking"),
    path("book/available-slots/", views.available_slots_api, name="available_slots_api"),
    path("booking/<int:booking_id>/edit/", views.edit_booking, name="edit_booking"),
    path("booking/<int:booking_id>/reschedule/", views.reschedule_booking, name="reschedule_booking"),
    path("booking/<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("booking-success/", views.booking_success, name="booking_success"),
]
