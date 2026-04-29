from django.contrib import admin

from django.contrib import admin
from .models import NailService

@admin.register(NailService)
class NailServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "price", "active")
    list_filter = ("active",)