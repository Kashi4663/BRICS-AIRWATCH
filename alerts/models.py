from django.conf import settings
from django.db import models
from django.utils import timezone

SEVERITY = [("CRITICAL", "Critical"), ("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")]
ALERT_STATUS = [("NEW", "New — requires verification"), ("ACKNOWLEDGED", "Acknowledged"), ("RESOLVED", "Resolved")]


class AuthorityAlert(models.Model):
    code = models.CharField(max_length=32, unique=True)
    hotspot = models.ForeignKey("pollution.Hotspot", null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts")
    severity = models.CharField(max_length=10, choices=SEVERITY)
    title = models.CharField(max_length=128)
    location = models.CharField(max_length=128)
    pollutant = models.CharField(max_length=16, default="PM2.5")
    current_value = models.FloatField()
    predicted_value = models.FloatField()
    unit = models.CharField(max_length=12, default="μg/m³")
    confidence = models.IntegerField()
    evidence = models.JSONField(default=list)
    status = models.CharField(max_length=14, choices=ALERT_STATUS, default="NEW")
    origin = models.CharField(max_length=48, default="AI pipeline (unverified)")
    created_at = models.DateTimeField(default=timezone.now)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def to_dict(self):
        return {
            "code": self.code,
            "hotspot": self.hotspot.code if self.hotspot else None,
            "severity": self.severity,
            "title": self.title,
            "location": self.location,
            "pollutant": self.pollutant,
            "current_value": round(self.current_value, 1),
            "predicted_value": round(self.predicted_value, 1),
            "unit": self.unit,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "status": self.status,
            "status_label": self.get_status_display(),
            "origin": self.origin,
            "created_at": self.created_at.isoformat(),
            "acknowledged_by": self.acknowledged_by.username if self.acknowledged_by else None,
            "resolved_by": self.resolved_by.username if self.resolved_by else None,
            "data_label": "DEMO DATA" if self.is_demo else "LIVE",
        }


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=48)
    target = models.CharField(max_length=64)
    detail = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
