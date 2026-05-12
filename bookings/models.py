from django.conf import settings
from django.db import models
from django.utils import timezone

from services.models import NailService


class AvailabilitySlot(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.start_time.strftime('%d %b %Y %H:%M')} - {self.end_time.strftime('%H:%M')}"


class Booking(models.Model):
    BOOKING_TYPE_CHOICES = [
        ("nails", "Nails"),
        ("toes", "Toes"),
        ("both", "Nails and Toes"),
    ]

    STATUS_CHOICES = [
        ("confirmed", "Confirmed"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash at appointment"),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    booking_type = models.CharField(
        max_length=20,
        choices=BOOKING_TYPE_CHOICES,
        default="nails",
    )

    nail_service = models.ForeignKey(
        NailService,
        on_delete=models.PROTECT,
        related_name="nail_bookings",
        null=True,
        blank=True,
    )

    toe_service = models.ForeignKey(
        NailService,
        on_delete=models.PROTECT,
        related_name="toe_bookings",
        null=True,
        blank=True,
    )

    nail_colour_notes = models.TextField(blank=True, default="")
    nail_vibe_notes = models.TextField(blank=True, default="")

    toe_colour_notes = models.TextField(blank=True, default="")
    toe_vibe_notes = models.TextField(blank=True, default="")

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="cash",
    )

    cash_confirmed = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="confirmed",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_duration_minutes(self):
        total = 0

        if self.nail_service:
            total += self.nail_service.duration_minutes

        if self.toe_service:
            total += self.toe_service.duration_minutes

        return total

    @property
    def total_price(self):
        total = 0

        if self.nail_service:
            total += self.nail_service.price

        if self.toe_service:
            total += self.toe_service.price

        return total

    def __str__(self):
        return f"{self.client.email} - {self.get_booking_type_display()}"


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="email_logs",
        null=True,
        blank=True,
    )

    subject = models.CharField(max_length=255)
    recipient_emails = models.TextField()
    payload = models.JSONField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    error_message = models.TextField(blank=True, null=True)
    attempts = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_sent(self):
        self.status = "sent"
        self.sent_at = timezone.now()
        self.last_attempt_at = timezone.now()
        self.error_message = ""
        self.save()

    def mark_failed(self, error_message):
        self.status = "failed"
        self.last_attempt_at = timezone.now()
        self.error_message = str(error_message)
        self.save()

    def __str__(self):
        return f"{self.subject} - {self.status}"
