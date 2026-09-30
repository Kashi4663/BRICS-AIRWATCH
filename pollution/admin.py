from django.contrib import admin

from .models import City, Country, CrossBorderEvent, HistoricalAQI, Hotspot, IndustrialZone, SatelliteObservation, SensorReading, WeatherObservation


@admin.register(Hotspot)
class HotspotAdmin(admin.ModelAdmin):
    list_display = ("code", "region", "aqi", "pm25", "status", "confidence", "is_demo")
    list_filter = ("status", "city__country")
    search_fields = ("code", "region")


for m in (Country, City, SensorReading, WeatherObservation, SatelliteObservation, IndustrialZone, HistoricalAQI, CrossBorderEvent):
    admin.site.register(m)
