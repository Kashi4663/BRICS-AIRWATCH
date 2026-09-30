from django.contrib import admin

from .models import CitizenReport


@admin.register(CitizenReport)
class CitizenReportAdmin(admin.ModelAdmin):
    list_display = ("code", "pollution_type", "location_label", "ai_label", "ai_confidence", "status", "created_at")
    list_filter = ("status", "pollution_type", "is_demo")
    search_fields = ("code", "location_label")
