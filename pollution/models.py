from django.db import models
from django.utils import timezone

STATUS_CHOICES = [("LOW", "Low"), ("MODERATE", "Moderate"), ("HIGH", "High"), ("CRITICAL", "Critical")]


class Country(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=64)
    lat = models.FloatField()
    lng = models.FloatField()
    shared_model_status = models.CharField(max_length=32, default="SIMULATED SYNC")
    model_version = models.CharField(max_length=24, default="v0.4-demo")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class City(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities")
    name = models.CharField(max_length=64)
    state = models.CharField(max_length=64, blank=True)
    lat = models.FloatField()
    lng = models.FloatField()
    base_aqi = models.IntegerField(default=100)
    is_industrial = models.BooleanField(default=False)

    class Meta:
        ordering = ["country__name", "name"]
        verbose_name_plural = "cities"

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class Hotspot(models.Model):
    code = models.CharField(max_length=32, unique=True)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL, related_name="hotspots")
    region = models.CharField(max_length=128)
    lat = models.FloatField()
    lng = models.FloatField()
    primary_pollutant = models.CharField(max_length=16, default="PM2.5")
    aqi = models.IntegerField()
    pm25 = models.FloatField()
    pm10 = models.FloatField()
    no2 = models.FloatField()
    so2 = models.FloatField()
    co = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    confidence = models.IntegerField()
    source_category = models.CharField(max_length=64)
    sources = models.JSONField(default=list)
    wind_dir = models.CharField(max_length=4, default="NE")
    wind_deg = models.IntegerField(default=45)
    wind_speed = models.FloatField(default=12)
    pm25_change = models.FloatField(default=1.0, help_text="Multiplier over change window")
    change_window_min = models.IntegerField(default=60)
    predicted_pm25 = models.FloatField(default=0)
    predicted_event = models.BooleanField(default=False)
    citizen_report_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=True)
    detected_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-aqi"]

    def __str__(self):
        return self.code

    def to_dict(self):
        return {
            "code": self.code,
            "region": self.region,
            "city": self.city.name if self.city else None,
            "country": self.city.country.name if self.city else None,
            "country_code": self.city.country.code if self.city else None,
            "lat": self.lat,
            "lng": self.lng,
            "primary_pollutant": self.primary_pollutant,
            "aqi": self.aqi,
            "pm25": round(self.pm25, 1),
            "pm10": round(self.pm10, 1),
            "no2": round(self.no2, 1),
            "so2": round(self.so2, 1),
            "co": round(self.co, 2),
            "status": self.status,
            "confidence": self.confidence,
            "source_category": self.source_category,
            "sources": self.sources,
            "wind_dir": self.wind_dir,
            "wind_deg": self.wind_deg,
            "wind_speed": self.wind_speed,
            "pm25_change": self.pm25_change,
            "change_window_min": self.change_window_min,
            "predicted_pm25": round(self.predicted_pm25, 1),
            "predicted_event": self.predicted_event,
            "citizen_report_count": self.citizen_report_count,
            "detected_at": self.detected_at.isoformat(),
            "data_label": "DEMO DATA" if self.is_demo else "LIVE DATA",
        }


class SensorReading(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="readings")
    hotspot = models.ForeignKey(Hotspot, null=True, blank=True, on_delete=models.CASCADE, related_name="readings")
    timestamp = models.DateTimeField(db_index=True)
    pm25 = models.FloatField()
    pm10 = models.FloatField()
    no2 = models.FloatField()
    so2 = models.FloatField()
    co = models.FloatField()
    aqi = models.IntegerField()
    is_demo = models.BooleanField(default=True)

    class Meta:
        ordering = ["timestamp"]


class WeatherObservation(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="weather")
    timestamp = models.DateTimeField(db_index=True)
    temperature = models.FloatField()
    humidity = models.FloatField()
    wind_speed = models.FloatField()
    wind_deg = models.IntegerField()
    rainfall = models.FloatField(default=0)
    is_demo = models.BooleanField(default=True)

    class Meta:
        ordering = ["timestamp"]


class SatelliteObservation(models.Model):
    OBS_TYPES = [
        ("thermal_anomaly", "Thermal anomaly"),
        ("fire", "Active fire"),
        ("aerosol", "Aerosol optical depth"),
        ("no2_column", "NO2 column"),
    ]
    hotspot = models.ForeignKey(Hotspot, null=True, blank=True, on_delete=models.SET_NULL, related_name="satellite")
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL)
    lat = models.FloatField()
    lng = models.FloatField()
    observed_at = models.DateTimeField()
    obs_type = models.CharField(max_length=20, choices=OBS_TYPES)
    intensity = models.FloatField()
    confidence = models.IntegerField()
    source = models.CharField(max_length=64, default="Demo observation (Earth Engine-ready)")
    is_demo = models.BooleanField(default=True)

    def to_dict(self):
        return {
            "lat": self.lat, "lng": self.lng, "type": self.obs_type,
            "type_label": self.get_obs_type_display(), "intensity": round(self.intensity, 2),
            "confidence": self.confidence, "observed_at": self.observed_at.isoformat(),
            "source": self.source, "data_label": "DEMO DATA" if self.is_demo else "LIVE DATA",
        }


class IndustrialZone(models.Model):
    name = models.CharField(max_length=128)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    lat = models.FloatField()
    lng = models.FloatField()
    sector = models.CharField(max_length=64)


class HistoricalAQI(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="history")
    date = models.DateField(db_index=True)
    aqi = models.IntegerField()
    pm25 = models.FloatField()
    pm10 = models.FloatField()
    fire_events = models.IntegerField(default=0)
    temperature = models.FloatField(default=25)
    humidity = models.FloatField(default=50)
    wind_speed = models.FloatField(default=10)
    is_demo = models.BooleanField(default=True)

    class Meta:
        ordering = ["date"]
        unique_together = ("city", "date")


class CrossBorderEvent(models.Model):
    code = models.CharField(max_length=32, unique=True)
    origin_label = models.CharField(max_length=64)
    affected_label = models.CharField(max_length=64)
    origin_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="outgoing_events")
    affected_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="incoming_events")
    origin_lat = models.FloatField()
    origin_lng = models.FloatField()
    affected_lat = models.FloatField()
    affected_lng = models.FloatField()
    corridor = models.CharField(max_length=96)
    direction = models.CharField(max_length=4)
    window = models.CharField(max_length=24)
    confidence = models.IntegerField()
    risk = models.CharField(max_length=10, choices=STATUS_CHOICES, default="HIGH")
    is_demo = models.BooleanField(default=True)

    def to_dict(self):
        return {
            "code": self.code, "origin": self.origin_label, "affected": self.affected_label,
            "origin_country": self.origin_country.name, "affected_country": self.affected_country.name,
            "origin_lat": self.origin_lat, "origin_lng": self.origin_lng,
            "affected_lat": self.affected_lat, "affected_lng": self.affected_lng,
            "corridor": self.corridor, "direction": self.direction, "window": self.window,
            "confidence": self.confidence, "risk": self.risk,
            "data_label": "SIMULATED PREDICTION",
        }
