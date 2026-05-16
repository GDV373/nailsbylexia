from datetime import timedelta
from urllib.parse import urljoin

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import requests

from services.models import NailService
from .models import AvailabilitySlot, Booking, EmailLog


def build_public_url(route_name):
    return urljoin(
        f"{settings.PUBLIC_SITE_URL}/",
        reverse(route_name).lstrip("/"),
    )


def send_booking_email(booking, subject_prefix, notification_type):
    relay_url = getattr(settings, "EMAIL_RELAY_URL", None)
    relay_secret = getattr(settings, "EMAIL_RELAY_SECRET", None)

    subject = f"{subject_prefix} - Nails by Lexia Booking"

    local_start = timezone.localtime(booking.start_time)
    local_end = timezone.localtime(booking.end_time)

    policies_url = build_public_url("policies_page")
    faq_url = build_public_url("faq_page")
    directions_url = settings.APPOINTMENT_MAPS_URL
    include_calendar_invite = notification_type in {"created", "updated", "cancelled"}
    calendar_method = "CANCEL" if notification_type == "cancelled" else "REQUEST"
    calendar_status = "CANCELLED" if notification_type == "cancelled" else "CONFIRMED"

    payload = {
        "subject": subject,
        "notification_type": notification_type,
        "customer_email": booking.client.email,
        "admin_email": getattr(settings, "ADMIN_BOOKING_EMAIL", None),

        "client_name": booking.client.username,
        "client_phone": booking.client.phone,

        "booking_type": booking.get_booking_type_display(),
        "booking_date": local_start.strftime("%d %B %Y"),
        "booking_time": f"{local_start.strftime('%H:%M')} to {local_end.strftime('%H:%M')}",
        "duration_minutes": booking.total_duration_minutes,
        "total_price": str(booking.total_price),
        "payment": booking.get_payment_method_display(),
        "status": booking.get_status_display(),

        "nail_service": booking.nail_service.name if booking.nail_service else None,
        "nail_colours": booking.nail_colour_notes or None,
        "nail_vibe": booking.nail_vibe_notes or None,

        "toe_service": booking.toe_service.name if booking.toe_service else None,
        "toe_colours": booking.toe_colour_notes or None,
        "toe_vibe": booking.toe_vibe_notes or None,

        "policy_url": policies_url,
        "faq_url": faq_url,
        "directions_url": directions_url,
        "location_name": settings.APPOINTMENT_LOCATION_NAME,
        "location_latitude": settings.APPOINTMENT_LOCATION_LATITUDE,
        "location_longitude": settings.APPOINTMENT_LOCATION_LONGITUDE,

        "location": {
            "name": settings.APPOINTMENT_LOCATION_NAME,
            "latitude": settings.APPOINTMENT_LOCATION_LATITUDE,
            "longitude": settings.APPOINTMENT_LOCATION_LONGITUDE,
            "maps_url": directions_url,
        },

    }

    if include_calendar_invite:
        payload.update({
            "booking_id": booking.id,
            "email_action": notification_type,
            "calendar_uid": f"booking-{booking.id}@nailsbylexia",
            "calendar_method": calendar_method,
            "calendar_status": calendar_status,
            "calendar_sequence": int(timezone.now().timestamp()),
            "start_iso": booking.start_time.isoformat(),
            "end_iso": booking.end_time.isoformat(),
        })

    recipients = []

    if booking.client.email:
        recipients.append(booking.client.email)

    admin_email = getattr(settings, "ADMIN_BOOKING_EMAIL", None)

    if admin_email:
        recipients.append(admin_email)

    recipients = list(dict.fromkeys(recipients))

    email_log = EmailLog.objects.create(
        booking=booking,
        subject=subject,
        recipient_emails=", ".join(recipients),
        payload=payload,
        status="pending",
    )

    if not relay_url or not relay_secret:
        email_log.status = "failed"
        email_log.error_message = "Email relay is not configured."
        email_log.attempts += 1
        email_log.last_attempt_at = timezone.now()
        email_log.save()

        print("Email relay is not configured. Email not sent.")
        return

    try:
        response = requests.post(
            relay_url,
            json=payload,
            headers={"X-Relay-Secret": relay_secret},
            timeout=25,
        )

        email_log.attempts += 1
        email_log.last_attempt_at = timezone.now()

        if response.status_code >= 400:
            email_log.status = "failed"
            email_log.error_message = f"{response.status_code} - {response.text}"
            email_log.save()

            print(f"Email relay failed: {response.status_code} - {response.text}")
            return

        email_log.status = "sent"
        email_log.sent_at = timezone.now()
        email_log.error_message = ""
        email_log.save()

    except Exception as e:
        email_log.attempts += 1
        email_log.last_attempt_at = timezone.now()
        email_log.status = "failed"
        email_log.error_message = str(e)
        email_log.save()

        print(f"Email relay error: {e}")


def get_available_slots(total_duration):
    available_slots = []
    now = timezone.now()

    availability_slots = list(
        AvailabilitySlot.objects.filter(
            active=True,
            end_time__gt=now
        ).order_by("start_time")
    )

    if not availability_slots:
        return available_slots

    earliest_start = min(slot.start_time for slot in availability_slots)
    latest_end = max(slot.end_time for slot in availability_slots)

    existing_bookings = list(
        Booking.objects.filter(
            status__in=["confirmed", "done"],
            start_time__lt=latest_end,
            end_time__gt=earliest_start,
        ).values("start_time", "end_time")
    )

    for slot in availability_slots:
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
                    microsecond=0,
                )
            else:
                current_time = current_time.replace(
                    minute=rounded_minute,
                    second=0,
                    microsecond=0,
                )

        while True:
            possible_end_time = current_time + timedelta(minutes=total_duration)

            if possible_end_time > slot.end_time:
                break

            overlap = False

            for booking in existing_bookings:
                if (
                    booking["start_time"] < possible_end_time
                    and booking["end_time"] > current_time
                ):
                    overlap = True
                    break

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
        local_start = timezone.localtime(slot["start"])
        local_end = timezone.localtime(slot["end"])

        month_key = local_start.strftime("%Y-%m")
        month_label = local_start.strftime("%B %Y")
        date_key = local_start.strftime("%Y-%m-%d")
        date_label = local_start.strftime("%a %d %b")

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
            "start": local_start.isoformat(),
            "end": local_end.isoformat(),
            "time_label": f"{local_start.strftime('%H:%M')} → {local_end.strftime('%H:%M')}",
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

        if start_time and timezone.is_naive(start_time):
            start_time = timezone.make_aware(
                start_time,
                timezone.get_current_timezone()
            )

        if end_time and timezone.is_naive(end_time):
            end_time = timezone.make_aware(
                end_time,
                timezone.get_current_timezone()
            )

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

        send_booking_email(booking, "New Booking", "created")
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
        booking.nail_colour_notes = request.POST.get(
            "nail_colour_notes",
            booking.nail_colour_notes
        ).strip()

        booking.nail_vibe_notes = request.POST.get(
            "nail_vibe_notes",
            booking.nail_vibe_notes
        ).strip()

        booking.toe_colour_notes = request.POST.get(
            "toe_colour_notes",
            booking.toe_colour_notes
        ).strip()

        booking.toe_vibe_notes = request.POST.get(
            "toe_vibe_notes",
            booking.toe_vibe_notes
        ).strip()

        booking.save()

        send_booking_email(booking, "Booking Updated", "updated")
        messages.success(request, "Booking updated successfully.")
        return redirect("account_dashboard")

    return render(request, "bookings/edit_booking.html", {"booking": booking})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)

    if request.method == "POST":
        booking.status = "cancelled"
        booking.save()

        send_booking_email(booking, "Booking Cancelled", "cancelled")
        messages.success(request, "Booking cancelled successfully.")
        return redirect("account_dashboard")

    return render(request, "bookings/cancel_booking.html", {"booking": booking})


def booking_success(request):
    return render(request, "bookings/booking_success.html")
