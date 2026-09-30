from django.contrib import admin

from .models import AuditLog, AuthorityAlert


@admin.register(AuthorityAlert)
class AuthorityAlertAdmin(admin.ModelAdmin):
    list_display = ("code", "severity", "location", "confidence", "status", "created_at")
    list_filter = ("severity", "status")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "target", "ip")
    readonly_fields = ("created_at", "user", "action", "target", "detail", "ip")
