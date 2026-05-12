import calendar
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.models import AvailabilitySlot, Booking
from bookings.views import send_booking_email
from services.models import NailService


User = get_user_model()


@staff_member_required
def availability_builder(request):
    months = [
        (1, "Jan"),
        (2, "Feb"),
        (3, "Mar"),
        (4, "Apr"),
        (5, "May"),
        (6, "Jun"),
        (7, "Jul"),
        (8, "Aug"),
        (9, "Sep"),
        (10, "Oct"),
        (11, "Nov"),
        (12, "Dec"),
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

    current_tz = timezone.get_current_timezone()
    today = timezone.localdate()

    week_start_raw = request.GET.get("week_start")

    if week_start_raw:
        try:
            selected_week_start = datetime.strptime(week_start_raw, "%Y-%m-%d").date()
        except ValueError:
            selected_week_start = today - timedelta(days=today.weekday())
    else:
        selected_week_start = today - timedelta(days=today.weekday())

    selected_week_start = selected_week_start - timedelta(days=selected_week_start.weekday())
    previous_week_start = selected_week_start - timedelta(days=7)
    next_week_start = selected_week_start + timedelta(days=7)

    week_days = []

    for i in range(7):
        date_obj = selected_week_start + timedelta(days=i)

        week_days.append({
            "date": date_obj,
            "date_iso": date_obj.strftime("%Y-%m-%d"),
            "date_display": date_obj.strftime("%d-%m-%Y"),
            "day_short": date_obj.strftime("%a"),
            "day_full": date_obj.strftime("%A"),
        })

    if request.method == "POST":
        entry_mode = request.POST.get("entry_mode", "bulk")

        if entry_mode == "weekly":
            weekly_dates = request.POST.getlist("weekly_date")
            weekly_starts = request.POST.getlist("weekly_start")
            weekly_ends = request.POST.getlist("weekly_end")

            created_count = 0
            skipped_count = 0

            for date_raw, start_raw, end_raw in zip(weekly_dates, weekly_starts, weekly_ends):
                if not date_raw or not start_raw or not end_raw:
                    skipped_count += 1
                    continue

                try:
                    date_obj = datetime.strptime(date_raw, "%Y-%m-%d").date()

                    start_hour, start_minute = map(int, start_raw.split(":"))
                    end_hour, end_minute = map(int, end_raw.split(":"))

                    start_dt = timezone.make_aware(
                        datetime.combine(date_obj, time(start_hour, start_minute)),
                        current_tz
                    )

                    end_dt = timezone.make_aware(
                        datetime.combine(date_obj, time(end_hour, end_minute)),
                        current_tz
                    )
                except (ValueError, TypeError):
                    skipped_count += 1
                    continue

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
                f"Weekly entry created {created_count} availability slot(s). "
                f"Skipped {skipped_count} duplicate/invalid slot(s)."
            )

            return redirect(f"{request.path}?week_start={selected_week_start.strftime('%Y-%m-%d')}")

        year = int(request.POST.get("year"))
        selected_months = [int(m) for m in request.POST.getlist("months")]
        selected_days = [int(d) for d in request.POST.getlist("weekdays")]

        weekday_start = request.POST.get("weekday_start")
        weekday_end = request.POST.get("weekday_end")
        weekend_start = request.POST.get("weekend_start")
        weekend_end = request.POST.get("weekend_end")

        created_count = 0
        skipped_count = 0

        for month in selected_months:
            _, days_in_month = calendar.monthrange(year, month)

            for day in range(1, days_in_month + 1):
                date_obj = datetime(year, month, day)
                weekday = date_obj.weekday()

                if weekday not in selected_days:
                    continue

                is_weekend = weekday in [5, 6]

                start_raw = weekend_start if is_weekend else weekday_start
                end_raw = weekend_end if is_weekend else weekday_end

                if not start_raw or not end_raw:
                    continue

                start_hour, start_minute = map(int, start_raw.split(":"))
                end_hour, end_minute = map(int, end_raw.split(":"))

                start_dt = datetime.combine(date_obj.date(), time(start_hour, start_minute))
                end_dt = datetime.combine(date_obj.date(), time(end_hour, end_minute))

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
            f"Created {created_count} availability slots. "
            f"Skipped {skipped_count} duplicates/invalid slots."
        )

        return redirect("availability_builder")

    slots = AvailabilitySlot.objects.order_by("start_time")

    return render(request, "dashboard/availability_builder.html", {
        "months": months,
        "weekdays": weekdays,
        "slots": slots,
        "current_year": timezone.now().year,
        "week_days": week_days,
        "selected_week_start": selected_week_start,
        "previous_week_start": previous_week_start,
        "next_week_start": next_week_start,
    })


@staff_member_required
def edit_availability(request, slot_id):
    slot = get_object_or_404(AvailabilitySlot, id=slot_id)

    if request.method == "POST":
        date_raw = request.POST.get("date")
        start_raw = request.POST.get("start_time")
        end_raw = request.POST.get("end_time")
        active = request.POST.get("active") == "on"

        current_tz = timezone.get_current_timezone()

        date_obj = datetime.strptime(date_raw, "%Y-%m-%d").date()

        start_hour, start_minute = map(int, start_raw.split(":"))
        end_hour, end_minute = map(int, end_raw.split(":"))

        start_dt = timezone.make_aware(
            datetime.combine(date_obj, time(start_hour, start_minute)),
            current_tz
        )

        end_dt = timezone.make_aware(
            datetime.combine(date_obj, time(end_hour, end_minute)),
            current_tz
        )

        if end_dt <= start_dt:
            messages.error(request, "End time must be after start time.")
            return redirect("edit_availability", slot_id=slot.id)

        slot.start_time = start_dt
        slot.end_time = end_dt
        slot.active = active
        slot.save()

        messages.success(request, "Availability updated.")
        return redirect("availability_builder")

    return render(request, "dashboard/edit_availability.html", {"slot": slot})


@staff_member_required
def delete_availability(request, slot_id):
    slot = get_object_or_404(AvailabilitySlot, id=slot_id)

    if request.method == "POST":
        slot.delete()
        messages.success(request, "Availability deleted.")
        return redirect("availability_builder")

    return render(request, "dashboard/delete_availability.html", {"slot": slot})


@staff_member_required
def services_manager(request):
    nail_services = NailService.objects.filter(service_area="nails").order_by("name")
    toe_services = NailService.objects.filter(service_area="toes").order_by("name")

    return render(request, "dashboard/services_manager.html", {
        "nail_services": nail_services,
        "toe_services": toe_services,
    })


@staff_member_required
def add_service(request):
    if request.method == "POST":
        service_area = request.POST.get("service_area")
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        duration_minutes = request.POST.get("duration_minutes")
        price = request.POST.get("price")
        active = request.POST.get("active") == "on"

        if service_area not in ["nails", "toes"]:
            messages.error(request, "Please choose a valid service area.")
            return redirect("add_service")

        if not name:
            messages.error(request, "Please enter a service name.")
            return redirect("add_service")

        if len(description) < 10:
            messages.error(request, "Please enter a service description of at least 10 characters.")
            return redirect("add_service")

        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError):
            messages.error(request, "Please enter a valid duration.")
            return redirect("add_service")

        if duration_minutes < 15:
            messages.error(request, "Duration must be at least 15 minutes.")
            return redirect("add_service")

        NailService.objects.create(
            service_area=service_area,
            name=name,
            description=description,
            duration_minutes=duration_minutes,
            price=price,
            active=active,
        )

        messages.success(request, "Service added.")
        return redirect("services_manager")

    return render(request, "dashboard/service_form.html", {
        "service": None,
        "title": "Add Service",
    })


@staff_member_required
def edit_service(request, service_id):
    service = get_object_or_404(NailService, id=service_id)

    if request.method == "POST":
        service_area = request.POST.get("service_area")
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        duration_minutes = request.POST.get("duration_minutes")
        price = request.POST.get("price")
        active = request.POST.get("active") == "on"

        if service_area not in ["nails", "toes"]:
            messages.error(request, "Please choose a valid service area.")
            return redirect("edit_service", service_id=service.id)

        if not name:
            messages.error(request, "Please enter a service name.")
            return redirect("edit_service", service_id=service.id)

        if len(description) < 10:
            messages.error(request, "Please enter a service description of at least 10 characters.")
            return redirect("edit_service", service_id=service.id)

        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError):
            messages.error(request, "Please enter a valid duration.")
            return redirect("edit_service", service_id=service.id)

        if duration_minutes < 15:
            messages.error(request, "Duration must be at least 15 minutes.")
            return redirect("edit_service", service_id=service.id)

        service.service_area = service_area
        service.name = name
        service.description = description
        service.duration_minutes = duration_minutes
        service.price = price
        service.active = active
        service.save()

        messages.success(request, "Service updated.")
        return redirect("services_manager")

    return render(request, "dashboard/service_form.html", {
        "service": service,
        "title": "Edit Service",
    })


@staff_member_required
def delete_service(request, service_id):
    service = get_object_or_404(NailService, id=service_id)

    if request.method == "POST":
        try:
            service.delete()
            messages.success(request, "Service deleted.")
        except ProtectedError:
            service.active = False
            service.save()
            messages.warning(
                request,
                "This service has existing bookings, so it cannot be deleted. "
                "It has been deactivated instead."
            )

        return redirect("services_manager")

    return render(request, "dashboard/delete_service.html", {"service": service})


@staff_member_required
def seed_default_services(request):
    items = [
        ("nails", "Gel-X", "Full cover soft gel extensions for a clean and long-lasting set.", 120, 20),
        ("nails", "Gelish", "Gel polish on natural nails with a glossy finish.", 90, 30),
        ("nails", "BIAB / Builder Gel", "Builder gel overlay for strength and natural nail growth.", 120, 35),
        ("nails", "Acrylic", "Strong nail extensions with custom shape and finish.", 150, 40),
        ("toes", "Toes Gelish", "Gel polish service for toes.", 60, 20),
        ("toes", "Toes Basic Polish", "Simple toe polish finish.", 45, 15),
        ("toes", "Toes With Art", "Toe polish with simple nail art.", 75, 25),
    ]

    for area, name, desc, duration, price in items:
        NailService.objects.update_or_create(
            name=name,
            defaults={
                "service_area": area,
                "description": desc,
                "duration_minutes": duration,
                "price": price,
                "active": True,
            }
        )

    messages.success(request, "Default nail and toe services added/updated.")
    return redirect("services_manager")


@staff_member_required
def admin_users(request):
    users = User.objects.all().order_by("-date_joined", "-id")
    return render(request, "dashboard/admin_users.html", {"users": users})


@staff_member_required
def toggle_user_staff(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        user_obj.is_staff = not user_obj.is_staff
        user_obj.save()
        messages.success(request, "Staff access updated.")

    return redirect("admin_users")


@staff_member_required
def toggle_user_active(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        if user_obj == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect("admin_users")

        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        messages.success(request, "Active status updated.")

    return redirect("admin_users")


@staff_member_required
def toggle_user_superuser(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        if user_obj == request.user:
            messages.error(request, "You cannot remove your own superuser access.")
            return redirect("admin_users")

        user_obj.is_superuser = not user_obj.is_superuser

        if user_obj.is_superuser:
            user_obj.is_staff = True

        user_obj.save()
        messages.success(request, "Superuser access updated.")

    return redirect("admin_users")


@staff_member_required
def admin_bookings(request):
    selected_date_raw = request.GET.get("date")
    today = timezone.localdate()

    if selected_date_raw:
        try:
            selected_date = datetime.strptime(selected_date_raw, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    all_bookings = Booking.objects.select_related(
        "client",
        "nail_service",
        "toe_service",
    ).order_by("start_time")

    upcoming_bookings = all_bookings.filter(
        status="confirmed",
        start_time__gte=timezone.now(),
    ).order_by("start_time")

    selected_day_bookings = all_bookings.filter(
        start_time__date=selected_date
    ).order_by("start_time")

    completed_bookings = all_bookings.filter(
        status="done"
    ).order_by("-start_time")[:30]

    cancelled_bookings = all_bookings.filter(
        status="cancelled"
    ).order_by("-start_time")[:30]

    return render(request, "dashboard/admin_bookings.html", {
        "selected_date": selected_date,
        "today": today,
        "upcoming_bookings": upcoming_bookings,
        "selected_day_bookings": selected_day_bookings,
        "completed_bookings": completed_bookings,
        "cancelled_bookings": cancelled_bookings,
    })


@staff_member_required
def complete_booking(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("client", "nail_service", "toe_service"),
        id=booking_id,
    )

    if request.method == "POST":
        if booking.status == "cancelled":
            messages.error(request, "Cancelled bookings cannot be completed.")
            return redirect("admin_bookings")

        booking.status = "done"
        booking.save()

        send_booking_email(booking, "Thank You - Booking Completed")

        messages.success(
            request,
            f"Booking for {booking.client.email or booking.client.username} marked as complete."
        )

    return redirect("admin_bookings")