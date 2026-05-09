from decimal import Decimal

from django.db import models
from django.utils import timezone


class StockItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ("consumable", "Consumable"),
        ("equipment", "Equipment"),
        ("tool", "Tool"),
        ("disposable", "Disposable"),
        ("other", "Other"),
    ]

    CATEGORY_CHOICES = [
        ("gel_polish", "Gel Polish"),
        ("builder_gel", "Builder Gel / BIAB"),
        ("base_coat", "Base Coat"),
        ("top_coat", "Top Coat"),
        ("acrylic", "Acrylic"),
        ("gel_x", "Gel-X"),
        ("nail_art", "Nail Art"),
        ("prep", "Prep / Cleaner"),
        ("removal", "Removal"),
        ("disposable", "Disposable"),
        ("equipment", "Equipment"),
        ("tool", "Tool"),
        ("other", "Other"),
    ]

    UNIT_TYPE_CHOICES = [
        ("bottle", "Bottle"),
        ("tube", "Tube"),
        ("pot", "Pot"),
        ("box", "Box"),
        ("pack", "Pack"),
        ("piece", "Piece"),
        ("tool", "Tool"),
        ("other", "Other"),
    ]

    SIZE_UNIT_CHOICES = [
        ("ml", "ml"),
        ("g", "g"),
        ("pcs", "pcs"),
        ("set", "set"),
        ("other", "Other"),
    ]

    barcode = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        help_text="EAN/UPC barcode if available.",
    )

    product_name = models.CharField(max_length=255)
    brand = models.CharField(max_length=120, blank=True)
    colour_name = models.CharField(max_length=120, blank=True)
    shade_code = models.CharField(max_length=80, blank=True)

    item_type = models.CharField(
        max_length=30,
        choices=ITEM_TYPE_CHOICES,
        default="consumable",
    )

    category = models.CharField(
        max_length=40,
        choices=CATEGORY_CHOICES,
        default="other",
    )

    unit_type = models.CharField(
        max_length=30,
        choices=UNIT_TYPE_CHOICES,
        default="bottle",
    )

    size_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Example: 5, 10, 100",
    )

    size_unit = models.CharField(
        max_length=20,
        choices=SIZE_UNIT_CHOICES,
        default="ml",
    )

    quantity_in_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    low_stock_alert = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost per item/unit bought.",
    )

    estimated_uses_per_item = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Example: 40 pairs of hands from one bottle.",
    )

    supplier = models.CharField(max_length=160, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    opened_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=120, blank=True)

    issuing_country = models.CharField(
        max_length=10,
        blank=True,
        help_text="Example: CN from EAN lookup.",
    )

    external_lookup_source = models.CharField(
        max_length=120,
        blank=True,
        help_text="Example: EAN-Search, manual, OCR.",
    )

    ocr_extracted_text = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    active = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_name", "brand"]

    def __str__(self):
        if self.brand:
            return f"{self.brand} - {self.product_name}"
        return self.product_name

    @property
    def is_low_stock(self):
        return self.quantity_in_stock <= self.low_stock_alert

    @property
    def estimated_cost_per_use(self):
        if not self.cost_price or not self.estimated_uses_per_item:
            return None

        if self.estimated_uses_per_item <= 0:
            return None

        return self.cost_price / Decimal(self.estimated_uses_per_item)

    @property
    def display_size(self):
        if self.size_value:
            return f"{self.size_value:g}{self.size_unit}"
        return "-"


class StockMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ("add", "Add Stock"),
        ("use", "Use Stock"),
        ("adjust", "Adjustment"),
        ("waste", "Waste / Damaged"),
        ("archive", "Archived"),
    ]

    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.CASCADE,
        related_name="movements",
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES,
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.stock_item} - {self.quantity}"