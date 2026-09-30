from django.db import models
from django.utils import timezone


class ForecastResult(models.Model):
    """Persisted forecast outputs (BigQuery table: forecast_results)."""

    hotspot = models.ForeignKey("pollution.Hotspot", null=True, blank=True, on_delete=models.CASCADE)
    city = models.ForeignKey("pollution.City", null=True, blank=True, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(default=timezone.now)
    horizon_hours = models.IntegerField()
    aqi = models.IntegerField()
    pm25 = models.FloatField()
    spike_probability = models.IntegerField()
    risk = models.CharField(max_length=10)
    confidence = models.IntegerField()
    model_source = models.CharField(max_length=32, default="SIMULATED")

    class Meta:
        ordering = ["-generated_at", "horizon_hours"]
