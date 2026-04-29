from django.conf import settings
from django.db import models
from services.models import NailService


class AvailabilitySlot(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    active = models.BooleanField(default=True)

    def duration_minutes(self):
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def __str__(self):
        return f"{self.start_time} to {self.end_time}"


class Booking(models.Model):
    BOOKING_TYPE_CHOICES = [
        ("nails", "Nails"),
        ("toes", "Toes"),
        ("both", "Nails and Toes"),
    ]

    PAYMENT_CHOICES = [
        ("cash", "Pay cash at appointment"),
    ]

    STATUS_CHOICES = [
        ("confirmed", "Confirmed"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES)

    nail_service = models.ForeignKey(
        NailService,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="nail_bookings"
    )

    toe_service = models.ForeignKey(
        NailService,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="toe_bookings"
    )

    nail_colour_notes = models.TextField(blank=True)
    nail_vibe_notes = models.TextField(blank=True)

    toe_colour_notes = models.TextField(blank=True)
    toe_vibe_notes = models.TextField(blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="cash"
    )

    cash_confirmed = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="confirmed")
    created_at = models.DateTimeField(auto_now_add=True)

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