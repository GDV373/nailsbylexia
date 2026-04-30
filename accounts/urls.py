from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("complete-profile/", views.complete_profile_view, name="complete_profile"),
    path("my-account/", views.account_dashboard_view, name="account_dashboard"),
    path("my-account/edit/", views.account_update_view, name="account_update"),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password, name="change_password"),
]