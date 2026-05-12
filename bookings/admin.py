import requests

from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone

from .models import AvailabilitySlot, Booking, EmailLog


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = (
        "start_time",
        "end_time",
        "active",
        "created_at",
    )

    list_filter = (
        "active",
        "start_time",
    )

    search_fields = (
        "start_time",
        "end_time",
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "booking_type",
        "start_time",
        "end_time",
        "status",
        "payment_method",
        "cash_confirmed",
        "created_at",
    )

    list_filter = (
        "booking_type",
        "status",
        "payment_method",
        "cash_confirmed",
        "start_time",
    )

    search_fields = (
        "client__email",
        "client__username",
        "client__phone",
        "nail_colour_notes",
        "nail_vibe_notes",
        "toe_colour_notes",
        "toe_vibe_notes",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


def retry_email_log(email_log):
    relay_url = getattr(settings, "EMAIL_RELAY_URL", None)
    relay_secret = getattr(settings, "EMAIL_RELAY_SECRET", None)

    if not relay_url or not relay_secret:
        email_log.status = "failed"
        email_log.error_message = "Email relay is not configured."
        email_log.last_attempt_at = timezone.now()
        email_log.attempts += 1
        email_log.save()
        return False, "Email relay is not configured."

    try:
        response = requests.post(
            relay_url,
            json=email_log.payload,
            headers={"X-Relay-Secret": relay_secret},
            timeout=8,
        )

        email_log.attempts += 1
        email_log.last_attempt_at = timezone.now()

        if response.status_code >= 400:
            email_log.status = "failed"
            email_log.error_message = f"{response.status_code} - {response.text}"
            email_log.save()
            return False, email_log.error_message

        email_log.status = "sent"
        email_log.sent_at = timezone.now()
        email_log.error_message = ""
        email_log.save()

        return True, "Sent"

    except Exception as e:
        email_log.attempts += 1
        email_log.last_attempt_at = timezone.now()
        email_log.status = "failed"
        email_log.error_message = str(e)
        email_log.save()

        return False, str(e)


@admin.action(description="Retry selected failed emails")
def retry_selected_emails(modeladmin, request, queryset):
    sent_count = 0
    failed_count = 0

    for email_log in queryset:
        success, _ = retry_email_log(email_log)

        if success:
            sent_count += 1
        else:
            failed_count += 1

    if sent_count:
        messages.success(request, f"{sent_count} email(s) resent successfully.")

    if failed_count:
        messages.warning(request, f"{failed_count} email(s) failed again. Check the error messages.")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "status",
        "attempts",
        "recipient_emails",
        "created_at",
        "last_attempt_at",
        "sent_at",
    )

    list_filter = (
        "status",
        "created_at",
        "last_attempt_at",
        "sent_at",
    )

    search_fields = (
        "subject",
        "recipient_emails",
        "error_message",
    )

    readonly_fields = (
        "booking",
        "subject",
        "recipient_emails",
        "payload",
        "status",
        "error_message",
        "attempts",
        "created_at",
        "last_attempt_at",
        "sent_at",
    )

    actions = [
        retry_selected_emails,
    ]
