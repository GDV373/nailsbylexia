from django.contrib import admin
from .models import AvailabilitySlot, Booking


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("start_time", "end_time", "active")
    list_filter = ("active",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "booking_type",
        "nail_service",
        "toe_service",
        "start_time",
        "end_time",
        "cash_confirmed",
        "status",
    )

    list_filter = ("booking_type", "status", "cash_confirmed")
    search_fields = ("client__email", "client__phone")
    readonly_fields = ("created_at",)