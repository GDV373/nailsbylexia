from decimal import Decimal, InvalidOperation
import os
import re

import requests
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import StockItem, StockMovement


def parse_decimal(value, default=None):
    if value in [None, ""]:
        return default

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def parse_int(value, default=None):
    if value in [None, ""]:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def guess_category_from_text(text):
    text_lower = text.lower()

    if "gel polish" in text_lower or "color gel" in text_lower or "colour gel" in text_lower:
        return "gel_polish"

    if "builder" in text_lower or "biab" in text_lower:
        return "builder_gel"

    if "top coat" in text_lower:
        return "top_coat"

    if "base coat" in text_lower:
        return "base_coat"

    if "acrylic" in text_lower:
        return "acrylic"

    if "cleaner" in text_lower or "prep" in text_lower:
        return "prep"

    if "remover" in text_lower or "removal" in text_lower:
        return "removal"

    return "other"


def guess_brand_from_text(text):
    known_brands = [
        "BORN PRETTY",
        "GUIBOFU",
        "VENALISA",
        "MODELONES",
        "BEETLES",
        "ROSALIND",
        "SAVILAND",
        "MEFA",
    ]

    text_upper = text.upper()

    for brand in known_brands:
        if brand in text_upper:
            return brand

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if lines:
        first_line = lines[0].strip()
        if len(first_line) <= 40:
            return first_line.upper()

    return ""


def guess_size_from_text(text):
    match = re.search(r"(\d+(?:\.\d+)?)\s*(ml|g|pcs|pc)", text, re.IGNORECASE)

    if not match:
        return "", "ml"

    value = match.group(1)
    unit = match.group(2).lower()

    if unit == "pc":
        unit = "pcs"

    return value, unit


def build_product_name_from_ocr(text):
    cleaned_lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if len(line) <= 2:
            continue

        cleaned_lines.append(line)

    if not cleaned_lines:
        return ""

    return " ".join(cleaned_lines[:4])


def get_known_barcode_data(barcode):
    known_items = {
        "6975708101578": {
            "found": True,
            "source": "EAN-Search manual confirmed",
            "barcode": "6975708101578",
            "product_name": "10ml Flow Light White Cat Magnetic Gel Nail Polish Ultra Shine Semi Permanent Soak Off",
            "brand": "BORN PRETTY",
            "colour_name": "Flow Light White Cat",
            "shade_code": "1578",
            "category": "gel_polish",
            "item_type": "consumable",
            "unit_type": "bottle",
            "size_value": "10",
            "size_unit": "ml",
            "issuing_country": "CN",
        }
    }

    return known_items.get(barcode)


@staff_member_required
def manage_stock(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    low_only = request.GET.get("low_stock") == "1"
    archived = request.GET.get("archived") == "1"

    items = StockItem.objects.all()

    if archived:
        items = items.filter(archived=True)
    else:
        items = items.filter(archived=False)

    if query:
        items = (
            items.filter(product_name__icontains=query)
            | items.filter(brand__icontains=query)
            | items.filter(barcode__icontains=query)
            | items.filter(colour_name__icontains=query)
            | items.filter(shade_code__icontains=query)
        )

    if category:
        items = items.filter(category=category)

    items = items.order_by("product_name", "brand")

    if low_only:
        items = [item for item in items if item.is_low_stock]

    low_stock_items = [
        item
        for item in StockItem.objects.filter(active=True, archived=False).order_by("product_name")
        if item.is_low_stock
    ]

    recent_movements = StockMovement.objects.select_related("stock_item").order_by("-created_at")[:12]

    return render(request, "stock/manage_stock.html", {
        "items": items,
        "low_stock_items": low_stock_items,
        "recent_movements": recent_movements,
        "query": query,
        "category": category,
        "low_only": low_only,
        "archived": archived,
        "category_choices": StockItem.CATEGORY_CHOICES,
    })


@staff_member_required
def add_stock_item(request):
    barcode_prefill = request.GET.get("barcode", "").strip()

    if request.method == "POST":
        barcode = request.POST.get("barcode", "").strip() or None

        if barcode:
            existing = StockItem.objects.filter(barcode=barcode).first()

            if existing:
                messages.info(request, "This barcode already exists. You can update the stock quantity here.")
                return redirect("edit_stock_item", item_id=existing.id)

        product_name = request.POST.get("product_name", "").strip()
        brand = request.POST.get("brand", "").strip()
        colour_name = request.POST.get("colour_name", "").strip()
        shade_code = request.POST.get("shade_code", "").strip()
        item_type = request.POST.get("item_type", "consumable")
        category = request.POST.get("category", "other")
        unit_type = request.POST.get("unit_type", "bottle")
        size_value = parse_decimal(request.POST.get("size_value"), None)
        size_unit = request.POST.get("size_unit", "ml")
        quantity_in_stock = parse_decimal(request.POST.get("quantity_in_stock"), Decimal("0"))
        low_stock_alert = parse_decimal(request.POST.get("low_stock_alert"), Decimal("1"))
        cost_price = parse_decimal(request.POST.get("cost_price"), None)
        estimated_uses_per_item = parse_int(request.POST.get("estimated_uses_per_item"), None)
        supplier = request.POST.get("supplier", "").strip()
        purchase_date = request.POST.get("purchase_date") or None
        expiry_date = request.POST.get("expiry_date") or None
        opened_date = request.POST.get("opened_date") or None
        location = request.POST.get("location", "").strip()
        issuing_country = request.POST.get("issuing_country", "").strip()
        external_lookup_source = request.POST.get("external_lookup_source", "").strip()
        ocr_extracted_text = request.POST.get("ocr_extracted_text", "").strip()
        notes = request.POST.get("notes", "").strip()
        active = request.POST.get("active") == "on"

        if not product_name:
            messages.error(request, "Product name is required.")
            return redirect("add_stock_item")

        item = StockItem.objects.create(
            barcode=barcode,
            product_name=product_name,
            brand=brand,
            colour_name=colour_name,
            shade_code=shade_code,
            item_type=item_type,
            category=category,
            unit_type=unit_type,
            size_value=size_value,
            size_unit=size_unit,
            quantity_in_stock=quantity_in_stock,
            low_stock_alert=low_stock_alert,
            cost_price=cost_price,
            estimated_uses_per_item=estimated_uses_per_item,
            supplier=supplier,
            purchase_date=purchase_date,
            expiry_date=expiry_date,
            opened_date=opened_date,
            location=location,
            issuing_country=issuing_country,
            external_lookup_source=external_lookup_source,
            ocr_extracted_text=ocr_extracted_text,
            notes=notes,
            active=active,
            archived=False,
        )

        if quantity_in_stock and quantity_in_stock > 0:
            StockMovement.objects.create(
                stock_item=item,
                movement_type="add",
                quantity=quantity_in_stock,
                note="Initial stock quantity",
            )

        messages.success(request, "Stock item added successfully.")
        return redirect("manage_stock")

    return render(request, "stock/stock_form.html", {
        "item": None,
        "title": "Add Stock Item",
        "barcode_prefill": barcode_prefill,
        "item_type_choices": StockItem.ITEM_TYPE_CHOICES,
        "category_choices": StockItem.CATEGORY_CHOICES,
        "unit_type_choices": StockItem.UNIT_TYPE_CHOICES,
        "size_unit_choices": StockItem.SIZE_UNIT_CHOICES,
    })


@staff_member_required
def edit_stock_item(request, item_id):
    item = get_object_or_404(StockItem, id=item_id)

    if request.method == "POST":
        barcode = request.POST.get("barcode", "").strip() or None

        if barcode:
            existing = StockItem.objects.filter(barcode=barcode).exclude(id=item.id).first()

            if existing:
                messages.error(request, "Another stock item already uses this barcode.")
                return redirect("edit_stock_item", item_id=item.id)

        product_name = request.POST.get("product_name", "").strip()

        if not product_name:
            messages.error(request, "Product name is required.")
            return redirect("edit_stock_item", item_id=item.id)

        item.barcode = barcode
        item.product_name = product_name
        item.brand = request.POST.get("brand", "").strip()
        item.colour_name = request.POST.get("colour_name", "").strip()
        item.shade_code = request.POST.get("shade_code", "").strip()
        item.item_type = request.POST.get("item_type", "consumable")
        item.category = request.POST.get("category", "other")
        item.unit_type = request.POST.get("unit_type", "bottle")
        item.size_value = parse_decimal(request.POST.get("size_value"), None)
        item.size_unit = request.POST.get("size_unit", "ml")
        item.quantity_in_stock = parse_decimal(request.POST.get("quantity_in_stock"), Decimal("0"))
        item.low_stock_alert = parse_decimal(request.POST.get("low_stock_alert"), Decimal("1"))
        item.cost_price = parse_decimal(request.POST.get("cost_price"), None)
        item.estimated_uses_per_item = parse_int(request.POST.get("estimated_uses_per_item"), None)
        item.supplier = request.POST.get("supplier", "").strip()
        item.purchase_date = request.POST.get("purchase_date") or None
        item.expiry_date = request.POST.get("expiry_date") or None
        item.opened_date = request.POST.get("opened_date") or None
        item.location = request.POST.get("location", "").strip()
        item.issuing_country = request.POST.get("issuing_country", "").strip()
        item.external_lookup_source = request.POST.get("external_lookup_source", "").strip()
        item.ocr_extracted_text = request.POST.get("ocr_extracted_text", "").strip()
        item.notes = request.POST.get("notes", "").strip()
        item.active = request.POST.get("active") == "on"
        item.save()

        messages.success(request, "Stock item updated successfully.")
        return redirect("manage_stock")

    return render(request, "stock/stock_form.html", {
        "item": item,
        "title": "Edit Stock Item",
        "barcode_prefill": "",
        "item_type_choices": StockItem.ITEM_TYPE_CHOICES,
        "category_choices": StockItem.CATEGORY_CHOICES,
        "unit_type_choices": StockItem.UNIT_TYPE_CHOICES,
        "size_unit_choices": StockItem.SIZE_UNIT_CHOICES,
    })


@staff_member_required
def adjust_stock(request, item_id):
    item = get_object_or_404(StockItem, id=item_id)

    if request.method == "POST":
        movement_type = request.POST.get("movement_type", "adjust")
        quantity = parse_decimal(request.POST.get("quantity"), Decimal("0"))
        note = request.POST.get("note", "").strip()

        if quantity <= 0:
            messages.error(request, "Quantity must be greater than 0.")
            return redirect("manage_stock")

        if movement_type == "add":
            item.quantity_in_stock += quantity
        elif movement_type in ["use", "waste"]:
            item.quantity_in_stock -= quantity

            if item.quantity_in_stock < 0:
                item.quantity_in_stock = Decimal("0")
        elif movement_type == "adjust":
            item.quantity_in_stock = quantity
        else:
            messages.error(request, "Invalid stock movement.")
            return redirect("manage_stock")

        item.save()

        StockMovement.objects.create(
            stock_item=item,
            movement_type=movement_type,
            quantity=quantity,
            note=note,
        )

        messages.success(request, "Stock updated.")
        return redirect("manage_stock")

    return redirect("manage_stock")


@staff_member_required
def archive_stock_item(request, item_id):
    item = get_object_or_404(StockItem, id=item_id)

    if request.method == "POST":
        item.archived = True
        item.active = False
        item.save()

        StockMovement.objects.create(
            stock_item=item,
            movement_type="archive",
            quantity=0,
            note="Item archived",
        )

        messages.success(request, "Stock item archived.")
        return redirect("manage_stock")

    return redirect("manage_stock")


@staff_member_required
def lookup_stock_by_barcode(request):
    barcode = request.GET.get("barcode", "").strip()

    if not barcode:
        return JsonResponse({
            "found": False,
            "message": "No barcode provided.",
        })

    item = StockItem.objects.filter(barcode=barcode).first()

    if not item:
        return JsonResponse({
            "found": False,
            "barcode": barcode,
            "message": "Barcode not found in your database.",
        })

    return JsonResponse({
        "found": True,
        "id": item.id,
        "barcode": item.barcode,
        "product_name": item.product_name,
        "brand": item.brand,
        "colour_name": item.colour_name,
        "shade_code": item.shade_code,
        "category": item.category,
        "category_display": item.get_category_display(),
        "item_type": item.item_type,
        "item_type_display": item.get_item_type_display(),
        "unit_type": item.unit_type,
        "size_value": str(item.size_value or ""),
        "size_unit": item.size_unit,
        "quantity_in_stock": str(item.quantity_in_stock),
        "low_stock_alert": str(item.low_stock_alert),
        "cost_price": str(item.cost_price or ""),
        "estimated_uses_per_item": item.estimated_uses_per_item or "",
        "supplier": item.supplier,
        "issuing_country": item.issuing_country,
        "external_lookup_source": item.external_lookup_source,
        "is_low_stock": item.is_low_stock,
        "edit_url": f"/stock/{item.id}/edit/",
    })


@staff_member_required
def external_barcode_lookup(request):
    barcode = request.GET.get("barcode", "").strip()

    if not barcode:
        return JsonResponse({
            "found": False,
            "message": "No barcode provided.",
        })

    item = StockItem.objects.filter(barcode=barcode).first()

    if item:
        return JsonResponse({
            "found": True,
            "source": "local_database",
            "already_in_db": True,
            "edit_url": f"/stock/{item.id}/edit/",
            "product_name": item.product_name,
            "brand": item.brand,
            "colour_name": item.colour_name,
            "shade_code": item.shade_code,
            "category": item.category,
            "item_type": item.item_type,
            "unit_type": item.unit_type,
            "size_value": str(item.size_value or ""),
            "size_unit": item.size_unit,
            "issuing_country": item.issuing_country,
        })

    known_data = get_known_barcode_data(barcode)

    if known_data:
        known_data["already_in_db"] = False
        return JsonResponse(known_data)

    return JsonResponse({
        "found": False,
        "already_in_db": False,
        "barcode": barcode,
        "message": "Barcode not found locally. No external API is connected yet.",
    })


@staff_member_required
@staff_member_required
def ocr_lookup(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request method.",
        }, status=405)

    image = request.FILES.get("image")

    if not image:
        return JsonResponse({
            "success": False,
            "message": "No image uploaded.",
        }, status=400)

    api_key = os.environ.get("OCR_SPACE_API_KEY")

    if not api_key:
        return JsonResponse({
            "success": False,
            "message": "OCR_SPACE_API_KEY is missing in Render environment variables.",
        }, status=400)

    try:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={
                "file": (
                    image.name or "stock-image.jpg",
                    image.read(),
                    image.content_type or "image/jpeg",
                )
            },
            data={
                "apikey": api_key,
                "language": "eng",
                "isOverlayRequired": "false",
                "detectOrientation": "true",
                "scale": "true",
                "OCREngine": "2",
            },
            timeout=18,
        )

    except requests.exceptions.Timeout:
        return JsonResponse({
            "success": False,
            "message": "OCR timed out. Try taking the photo closer, crop the label, or use better lighting.",
        }, status=504)

    except Exception as exc:
        return JsonResponse({
            "success": False,
            "message": f"OCR request failed before reaching OCR.space: {repr(exc)}",
        }, status=500)

    try:
        result = response.json()
    except Exception:
        return JsonResponse({
            "success": False,
            "message": f"OCR service did not return JSON. Status: {response.status_code}. Response: {response.text[:300]}",
        }, status=500)

    if response.status_code != 200:
        return JsonResponse({
            "success": False,
            "message": f"OCR.space returned HTTP {response.status_code}: {result}",
        }, status=500)

    if result.get("IsErroredOnProcessing"):
        error_message = result.get("ErrorMessage") or result.get("ErrorDetails") or "OCR failed."

        if isinstance(error_message, list):
            error_message = " ".join(str(x) for x in error_message)

        return JsonResponse({
            "success": False,
            "message": str(error_message),
        }, status=400)

    parsed_results = result.get("ParsedResults", [])

    if not parsed_results:
        return JsonResponse({
            "success": False,
            "message": "No OCR result returned. Try a clearer photo with better lighting.",
        }, status=404)

    extracted_text = parsed_results[0].get("ParsedText", "").strip()

    if not extracted_text:
        return JsonResponse({
            "success": False,
            "message": "No readable text detected. Try taking the photo closer and straight-on.",
        }, status=404)

    brand = guess_brand_from_text(extracted_text)
    product_name = build_product_name_from_ocr(extracted_text)
    category = guess_category_from_text(extracted_text)
    size_value, size_unit = guess_size_from_text(extracted_text)

    colour_name = ""
    text_lower = extracted_text.lower()

    if "yellow" in text_lower:
        colour_name = "Yellow"
    elif "white" in text_lower:
        colour_name = "White"
    elif "black" in text_lower:
        colour_name = "Black"
    elif "pink" in text_lower:
        colour_name = "Pink"
    elif "red" in text_lower:
        colour_name = "Red"
    elif "blue" in text_lower:
        colour_name = "Blue"
    elif "green" in text_lower:
        colour_name = "Green"
    elif "nude" in text_lower:
        colour_name = "Nude"

    return JsonResponse({
        "success": True,
        "source": "OCR.space",
        "ocr_extracted_text": extracted_text,
        "brand": brand,
        "product_name": product_name,
        "category": category,
        "item_type": "consumable",
        "unit_type": "bottle",
        "size_value": size_value,
        "size_unit": size_unit,
        "colour_name": colour_name,
    })