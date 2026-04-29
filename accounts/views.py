from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from bookings.models import Booking
from .forms import RegisterForm, LoginForm, CompleteProfileForm, AccountUpdateForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("account_dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.email_verified = True
            user.save()

            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("create_booking")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("account_dashboard")

    next_url = request.GET.get("next", "create_booking")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if not user.phone:
                return redirect("complete_profile")

            return redirect(request.POST.get("next") or "create_booking")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {
        "form": form,
        "next": next_url,
    })


@login_required
def complete_profile_view(request):
    if request.user.phone:
        return redirect("create_booking")

    if request.method == "POST":
        form = CompleteProfileForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Profile completed successfully.")
            return redirect("create_booking")
    else:
        form = CompleteProfileForm(instance=request.user)

    return render(request, "accounts/complete_profile.html", {"form": form})


@login_required
def account_dashboard_view(request):
    if not request.user.phone:
        return redirect("complete_profile")

    bookings = Booking.objects.filter(client=request.user).order_by("-created_at")

    return render(request, "accounts/account_dashboard.html", {
        "bookings": bookings,
    })


@login_required
def account_update_view(request):
    if not request.user.phone:
        return redirect("complete_profile")
        
    if request.method == "POST":
        form = AccountUpdateForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Your account details were updated.")
            return redirect("account_dashboard")
    else:
        form = AccountUpdateForm(instance=request.user)

    return render(request, "accounts/account_update.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")