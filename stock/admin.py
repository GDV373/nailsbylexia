from django.contrib import admin

from .models import StockItem, StockMovement


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = (
        "product_name",
        "brand",
        "colour_name",
        "barcode",
        "category",
        "item_type",
        "quantity_in_stock",
        "low_stock_alert",
        "cost_price",
        "estimated_uses_per_item",
        "active",
        "archived",
    )

    list_filter = (
        "category",
        "item_type",
        "unit_type",
        "active",
        "archived",
    )

    search_fields = (
        "barcode",
        "product_name",
        "brand",
        "colour_name",
        "shade_code",
        "supplier",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "stock_item",
        "movement_type",
        "quantity",
        "note",
        "created_at",
    )

    list_filter = (
        "movement_type",
        "created_at",
    )

    search_fields = (
        "stock_item__product_name",
        "stock_item__barcode",
        "stock_item__brand",
        "note",
    )