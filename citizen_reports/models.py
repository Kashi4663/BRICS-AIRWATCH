from django.conf import settings
from django.db import models
from django.utils import timezone

POLLUTION_TYPES = [
    ("smoke", "Smoke"),
    ("dust", "Dust"),
    ("industrial", "Industrial emission"),
    ("crop_burning", "Crop burning"),
    ("garbage_burning", "Garbage burning"),
    ("unknown", "Unknown"),
]

REPORT_STATUS = [
    ("SUBMITTED", "Submitted"),
    ("AWAITING_VERIFICATION", "Awaiting multi-source verification"),
    ("CORROBORATED", "Corroborated by other sources"),
    ("DISMISSED", "Dismissed"),
]


class CitizenReport(models.Model):
    code = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    image = models.FileField(upload_to="reports/%Y/%m/", blank=True)
    pollution_type = models.CharField(max_length=20, choices=POLLUTION_TYPES, default="unknown")
    description = models.TextField(blank=True, max_length=1000)
    lat = models.FloatField()
    lng = models.FloatField()
    location_label = models.CharField(max_length=128, blank=True)
    city = models.ForeignKey("pollution.City", null=True, blank=True, on_delete=models.SET_NULL)
    hotspot = models.ForeignKey("pollution.Hotspot", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    language = models.CharField(max_length=8, default="en")
    voice_transcript = models.TextField(blank=True)
    translated_text = models.TextField(blank=True)
    ai_category = models.CharField(max_length=40, blank=True)
    ai_label = models.CharField(max_length=96, blank=True)
    ai_confidence = models.IntegerField(null=True, blank=True)
    ai_indicators = models.JSONField(default=list, blank=True)
    ai_source = models.CharField(max_length=24, blank=True)
    status = models.CharField(max_length=24, choices=REPORT_STATUS, default="SUBMITTED")
    is_demo = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def to_dict(self):
        return {
            "code": self.code,
            "pollution_type": self.pollution_type,
            "pollution_type_label": self.get_pollution_type_display(),
            "description": self.description,
            "lat": self.lat,
            "lng": self.lng,
            "location_label": self.location_label,
            "city": self.city.name if self.city else None,
            "hotspot": self.hotspot.code if self.hotspot else None,
            "language": self.language,
            "ai_label": self.ai_label,
            "ai_confidence": self.ai_confidence,
            "ai_indicators": self.ai_indicators,
            "ai_source": self.ai_source,
            "status": self.status,
            "status_label": self.get_status_display(),
            "image_url": self.image.url if self.image else None,
            "created_at": self.created_at.isoformat(),
            "data_label": "DEMO DATA" if self.is_demo else "CITIZEN SUBMISSION",
        }
