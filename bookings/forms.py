from django import forms
from .models import Booking


class BookingForm(forms.ModelForm):
    cash_confirmed = forms.BooleanField(
        required=True,
        label="I will pay cash at the appointment",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    class Meta:
        model = Booking
        fields = [
            "booking_type",
            "nail_service",
            "toe_service",
            "nail_colour_notes",
            "nail_vibe_notes",
            "toe_colour_notes",
            "toe_vibe_notes",
            "cash_confirmed",
        ]