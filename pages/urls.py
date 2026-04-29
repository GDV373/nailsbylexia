from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("services/", views.services_page, name="services_page"),
    path("contact/", views.contact_page, name="contact_page"),
]