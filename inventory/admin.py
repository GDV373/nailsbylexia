from django.contrib import admin

from django.contrib import admin
from .models import ConsumableProduct, ServiceConsumable

@admin.register(ConsumableProduct)
class ConsumableProductAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "cost_per_unit", "stock_quantity")


@admin.register(ServiceConsumable)
class ServiceConsumableAdmin(admin.ModelAdmin):
    list_display = ("service", "product", "quantity_used")