import calendar
from datetime import datetime, time

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.utils import timezone

from bookings.models import AvailabilitySlot, Booking
from services.models import NailService


User = get_user_model()


@staff_member_required
def availability_builder(request):
    months = [
        (1, "Jan"), (2, "Feb"), (3, "Mar"), (4, "Apr"),
        (5, "May"), (6, "Jun"), (7, "Jul"), (8, "Aug"),
        (9, "Sep"), (10, "Oct"), (11, "Nov"), (12, "Dec"),
    ]

    weekdays = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    if request.method == "POST":
        year = int(request.POST.get("year"))
        selected_months = [int(m) for m in request.POST.getlist("months")]
        selected_days = [int(d) for d in request.POST.getlist("weekdays")]

        weekday_start = request.POST.get("weekday_start")
        weekday_end = request.POST.get("weekday_end")
        weekend_start = request.POST.get("weekend_start")
        weekend_end = request.POST.get("weekend_end")

        created_count = 0
        skipped_count = 0
        current_tz = timezone.get_current_timezone()

        for month in selected_months:
            _, days_in_month = calendar.monthrange(year, month)

            for day in range(1, days_in_month + 1):
                date_obj = datetime(year, month, day)
                weekday = date_obj.weekday()

                if weekday not in selected_days:
                    continue

                is_weekend = weekday in [5, 6]

                if is_weekend:
                    start_raw = weekend_start
                    end_raw = weekend_end
                else:
                    start_raw = weekday_start
                    end_raw = weekday_end

                if not start_raw or not end_raw:
                    continue

                start_hour, start_minute = map(int, start_raw.split(":"))
                end_hour, end_minute = map(int, end_raw.split(":"))

                start_dt = datetime.combine(
                    date_obj.date(),
                    time(start_hour, start_minute)
                )

                end_dt = datetime.combine(
                    date_obj.date(),
                    time(end_hour, end_minute)
                )

                start_dt = timezone.make_aware(start_dt, current_tz)
                end_dt = timezone.make_aware(end_dt, current_tz)

                if end_dt <= start_dt:
                    skipped_count += 1
                    continue

                exists = AvailabilitySlot.objects.filter(
                    start_time=start_dt,
                    end_time=end_dt,
                ).exists()

                if exists:
                    skipped_count += 1
                    continue

                AvailabilitySlot.objects.create(
                    start_time=start_dt,
                    end_time=end_dt,
                    active=True,
                )

                created_count += 1

        messages.success(
            request,
            f"Created {created_count} availability slots. Skipped {skipped_count} duplicates/invalid slots."
        )

        return redirect("availability_builder")

    slots = AvailabilitySlot.objects.order_by("-start_time")[:20]

    return render(request, "dashboard/availability_builder.html", {
        "months": months,
        "weekdays": weekdays,
        "slots": slots,
        "current_year": timezone.now().year,
    })


@staff_member_required
def admin_users(request):
    users = User.objects.all().order_by("-date_joined", "-id")

    return render(request, "dashboard/admin_users.html", {
        "users": users,
    })


@staff_member_required
def toggle_user_staff(request, user_id):
    user_obj = User.objects.get(id=user_id)

    if request.method == "POST":
        user_obj.is_staff = not user_obj.is_staff
        user_obj.save()

        messages.success(
            request,
            f"Staff access updated for {user_obj.email or user_obj.username}."
        )

    return redirect("admin_users")


@staff_member_required
def toggle_user_active(request, user_id):
    user_obj = User.objects.get(id=user_id)

    if request.method == "POST":
        if user_obj == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect("admin_users")

        user_obj.is_active = not user_obj.is_active
        user_obj.save()

        messages.success(
            request,
            f"Active status updated for {user_obj.email or user_obj.username}."
        )

    return redirect("admin_users")


@staff_member_required
def toggle_user_superuser(request, user_id):
    user_obj = User.objects.get(id=user_id)

    if request.method == "POST":
        if user_obj == request.user:
            messages.error(request, "You cannot remove your own superuser access.")
            return redirect("admin_users")

        user_obj.is_superuser = not user_obj.is_superuser

        if user_obj.is_superuser:
            user_obj.is_staff = True

        user_obj.save()

        messages.success(
            request,
            f"Superuser access updated for {user_obj.email or user_obj.username}."
        )

    return redirect("admin_users")