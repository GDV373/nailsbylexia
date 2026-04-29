from django.db import models

from django.db import models
from services.models import NailService

class ConsumableProduct(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=30, default="ml")
    cost_per_unit = models.DecimalField(max_digits=8, decimal_places=2)
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class ServiceConsumable(models.Model):
    service = models.ForeignKey(NailService, on_delete=models.CASCADE)
    product = models.ForeignKey(ConsumableProduct, on_delete=models.CASCADE)
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.service} uses {self.quantity_used} {self.product.unit} of {self.product}"