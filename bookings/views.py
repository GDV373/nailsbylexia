from datetime import timedelta, timezone as dt_timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from services.models import NailService
from .models import AvailabilitySlot, Booking


def send_booking_email(booking, subject_prefix):
    subject = f"{subject_prefix} - Nail Art Studio Booking"

    body = f"""
Booking Summary

Client: {booking.client.username}
Email: {booking.client.email}
Phone: {booking.client.phone}

Booking Type: {booking.get_booking_type_display()}

Nail Service: {booking.nail_service.name if booking.nail_service else "Not selected"}
Nail Colours: {booking.nail_colour_notes or "N/A"}
Nail Vibe: {booking.nail_vibe_notes or "N/A"}

Toe Service: {booking.toe_service.name if booking.toe_service else "Not selected"}
Toe Colours: {booking.toe_colour_notes or "N/A"}
Toe Vibe: {booking.toe_vibe_notes or "N/A"}

Date: {booking.start_time.strftime("%d %B %Y")}
Time: {booking.start_time.strftime("%H:%M")} to {booking.end_time.strftime("%H:%M")}

Total Duration: {booking.total_duration_minutes} minutes
Total Price: €{booking.total_price}
Payment: {booking.get_payment_method_display()}
Status: {booking.get_status_display()}
"""

    admin_email = getattr(settings, "ADMIN_BOOKING_EMAIL", None)

    recipients = [booking.client.email]

    if admin_email:
        recipients.append(admin_email)

    method = "CANCEL" if booking.status == "cancelled" else "REQUEST"
    event_status = "CANCELLED" if booking.status == "cancelled" else "CONFIRMED"

    uid = f"booking-{booking.id}@nailartstudio.local"

    start_utc = booking.start_time.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    end_utc = booking.end_time.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    created_utc = booking.created_at.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now_utc = timezone.now().astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    summary = f"Nail Art Appointment - {booking.get_booking_type_display()}"
    description = body.replace("\n", "\\n")

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Nail Art Studio//Booking System//EN
CALSCALE:GREGORIAN
METHOD:{method}
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now_utc}
DTSTART:{start_utc}
DTEND:{end_utc}
CREATED:{created_utc}
LAST-MODIFIED:{now_utc}
SUMMARY:{summary}
DESCRIPTION:{description}
STATUS:{event_status}
SEQUENCE:{1 if booking.status == "cancelled" else 0}
END:VEVENT
END:VCALENDAR
"""

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )

    filename = "booking-cancelled.ics" if booking.status == "cancelled" else "booking.ics"

    email.attach(
        filename,
        ics_content,
        "text/calendar"
    )

    email.send(fail_silently=False)


def get_available_slots(total_duration):
    available_slots = []
    now = timezone.now()

    existing_bookings = Booking.objects.filter(
        status__in=["confirmed", "done"]
    )

    for slot in AvailabilitySlot.objects.filter(
        active=True,
        end_time__gt=now
    ).order_by("start_time"):

        current_time = slot.start_time

        if current_time < now:
            current_time = now

            minute = current_time.minute
            rounded_minute = ((minute + 14) // 15) * 15

            if rounded_minute == 60:
                current_time = current_time + timedelta(hours=1)
                current_time = current_time.replace(
                    minute=0,
                    second=0,
                    microsecond=0
                )
            else:
                current_time = current_time.replace(
                    minute=rounded_minute,
                    second=0,
                    microsecond=0
                )

        while True:
            possible_end_time = current_time + timedelta(minutes=total_duration)

            if possible_end_time > slot.end_time:
                break

            overlap = existing_bookings.filter(
                start_time__lt=possible_end_time,
                end_time__gt=current_time
            ).exists()

            if not overlap:
                available_slots.append({
                    "start": current_time,
                    "end": possible_end_time,
                })

            current_time = current_time + timedelta(minutes=15)

    return available_slots


@login_required
def available_slots_api(request):
    duration = request.GET.get("duration")

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return JsonResponse({"months": []})

    slots = get_available_slots(duration)

    grouped = {}

    for slot in slots:
        month_key = slot["start"].strftime("%Y-%m")
        month_label = slot["start"].strftime("%B %Y")
        date_key = slot["start"].strftime("%Y-%m-%d")
        date_label = slot["start"].strftime("%a %d %b")

        if month_key not in grouped:
            grouped[month_key] = {
                "month_key": month_key,
                "month_label": month_label,
                "dates": {}
            }

        if date_key not in grouped[month_key]["dates"]:
            grouped[month_key]["dates"][date_key] = {
                "date_key": date_key,
                "date_label": date_label,
                "slots": []
            }

        grouped[month_key]["dates"][date_key]["slots"].append({
            "start": slot["start"].isoformat(),
            "end": slot["end"].isoformat(),
            "time_label": f'{slot["start"].strftime("%H:%M")} → {slot["end"].strftime("%H:%M")}',
        })

    months = []

    for month in grouped.values():
        month["dates"] = list(month["dates"].values())
        months.append(month)

    return JsonResponse({"months": months})


@login_required
def create_booking(request):
    if not request.user.phone:
        return redirect("complete_profile")

    nail_services = NailService.objects.filter(
        active=True,
        service_area="nails"
    ).order_by("price", "name")

    toe_services = NailService.objects.filter(
        active=True,
        service_area="toes"
    ).order_by("price", "name")

    if request.method == "POST":
        booking_type = request.POST.get("booking_type")
        nail_service_id = request.POST.get("nail_service")
        toe_service_id = request.POST.get("toe_service")

        nail_service = NailService.objects.filter(
            id=nail_service_id,
            service_area="nails",
            active=True
        ).first() if nail_service_id else None

        toe_service = NailService.objects.filter(
            id=toe_service_id,
            service_area="toes",
            active=True
        ).first() if toe_service_id else None

        start_time = parse_datetime(request.POST.get("start_time", ""))
        end_time = parse_datetime(request.POST.get("end_time", ""))

        nail_colour_notes = request.POST.get("nail_colour_notes", "").strip()
        nail_vibe_notes = request.POST.get("nail_vibe_notes", "").strip()
        toe_colour_notes = request.POST.get("toe_colour_notes", "").strip()
        toe_vibe_notes = request.POST.get("toe_vibe_notes", "").strip()
        cash_confirmed = request.POST.get("cash_confirmed") == "on"

        if booking_type not in ["nails", "toes", "both"]:
            messages.error(request, "Please choose nails, toes, or both.")
            return redirect("create_booking")

        if booking_type in ["nails", "both"] and not nail_service:
            messages.error(request, "Please choose a nail service.")
            return redirect("create_booking")

        if booking_type in ["toes", "both"] and not toe_service:
            messages.error(request, "Please choose a toe service.")
            return redirect("create_booking")

        if booking_type in ["nails", "both"] and (not nail_colour_notes or not nail_vibe_notes):
            messages.error(request, "Please add nail colour and vibe notes.")
            return redirect("create_booking")

        if booking_type in ["toes", "both"] and (not toe_colour_notes or not toe_vibe_notes):
            messages.error(request, "Please add toe colour and vibe notes.")
            return redirect("create_booking")

        if not start_time or not end_time:
            messages.error(request, "Please select an available time.")
            return redirect("create_booking")

        if not cash_confirmed:
            messages.error(request, "Please confirm cash payment at appointment.")
            return redirect("create_booking")

        overlap = Booking.objects.filter(
            status__in=["confirmed", "done"],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if overlap:
            messages.error(request, "This time has already been booked. Please choose another time.")
            return redirect("create_booking")

        booking = Booking.objects.create(
            client=request.user,
            booking_type=booking_type,
            nail_service=nail_service,
            toe_service=toe_service,
            nail_colour_notes=nail_colour_notes,
            nail_vibe_notes=nail_vibe_notes,
            toe_colour_notes=toe_colour_notes,
            toe_vibe_notes=toe_vibe_notes,
            start_time=start_time,
            end_time=end_time,
            payment_method="cash",
            cash_confirmed=True,
            status="confirmed",
        )

        send_booking_email(booking, "New Booking")
        messages.success(request, "Booking confirmed successfully.")
        return redirect("account_dashboard")

    return render(request, "bookings/create_booking.html", {
        "nail_services": nail_services,
        "toe_services": toe_services,
    })


@login_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)

    if booking.status == "cancelled":
        messages.error(request, "Cancelled bookings cannot be edited.")
        return redirect("account_dashboard")

    if request.method == "POST":
        booking.nail_colour_notes = request.POST.get("nail_colour_notes", booking.nail_colour_notes).strip()
        booking.nail_vibe_notes = request.POST.get("nail_vibe_notes", booking.nail_vibe_notes).strip()
        booking.toe_colour_notes = request.POST.get("toe_colour_notes", booking.toe_colour_notes).strip()
        booking.toe_vibe_notes = request.POST.get("toe_vibe_notes", booking.toe_vibe_notes).strip()
        booking.save()

        send_booking_email(booking, "Booking Updated")
        messages.success(request, "Booking updated successfully.")
        return redirect("account_dashboard")

    return render(request, "bookings/edit_booking.html", {"booking": booking})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)

    if request.method == "POST":
        booking.status = "cancelled"
        booking.save()

        send_booking_email(booking, "Booking Cancelled")
        messages.success(request, "Booking cancelled successfully.")
        return redirect("account_dashboard")

    return render(request, "bookings/cancel_booking.html", {"booking": booking})


def booking_success(request):
    return render(request, "bookings/booking_success.html")