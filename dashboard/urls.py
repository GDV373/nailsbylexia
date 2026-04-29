from django.urls import path
from . import views

urlpatterns = [
    path("availability/", views.availability_builder, name="availability_builder"),
]