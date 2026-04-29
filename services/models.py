from django.db import models


class NailService(models.Model):
    SERVICE_AREA_CHOICES = [
        ("nails", "Nails"),
        ("toes", "Toes"),
    ]

    name = models.CharField(max_length=100)
    service_area = models.CharField(
        max_length=20,
        choices=SERVICE_AREA_CHOICES,
        default="nails"
    )
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_service_area_display()} - {self.name}"