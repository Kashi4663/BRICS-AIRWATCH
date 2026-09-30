"""Shared intelligence helpers: geo maths, evidence chain, context gathering.
Kept out of views so AI / forecasting / geospatial logic is reusable."""
import math

from django.utils import timezone

from .config import DEMO


def haversine(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def pm25_to_aqi(pm25: float) -> int:
    """Indian NAQI sub-index for PM2.5 (24h breakpoints)."""
    bps = [(0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200), (91, 120, 201, 300), (121, 250, 301, 400), (251, 500, 401, 500)]
    for lo, hi, alo, ahi in bps:
        if pm25 <= hi:
            return int(round(alo + (ahi - alo) * (max(pm25, lo) - lo) / (hi - lo)))
    return 500


def aqi_status(aqi: int) -> str:
    if aqi >= 300:
        return "CRITICAL"
    if aqi >= 200:
        return "HIGH"
    if aqi >= 100:
        return "MODERATE"
    return "LOW"


def latest_weather(city):
    if city is None:
        return {}
    w = city.weather.order_by("-timestamp").first()
    if not w:
        return {}
    compass = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return {
        "temperature": w.temperature, "humidity": w.humidity, "wind_speed": w.wind_speed,
        "wind_deg": w.wind_deg, "wind_dir": compass[int((w.wind_deg + 22.5) // 45) % 8],
        "rainfall": w.rainfall, "timestamp": w.timestamp.isoformat(), "label": DEMO if w.is_demo else "LIVE DATA",
    }


def nearby_context(lat, lng):
    from citizen_reports.models import CitizenReport
    from pollution.models import Hotspot

    since = timezone.now() - timezone.timedelta(hours=24)
    box = 0.05  # ~5 km prefilter
    candidates = CitizenReport.objects.filter(lat__range=(lat - box, lat + box), lng__range=(lng - box, lng + box), created_at__gte=since)
    within = [r for r in candidates if haversine(lat, lng, r.lat, r.lng) <= 3]
    nearest, dist = None, None
    for h in Hotspot.objects.filter(is_active=True):
        d = haversine(lat, lng, h.lat, h.lng)
        if dist is None or d < dist:
            nearest, dist = h, d
    return {
        "reports_within_3km": len(within),
        "nearest_hotspot": nearest.code if nearest else None,
        "nearest_hotspot_obj": nearest,
        "distance_km": round(dist, 1) if dist is not None else None,
    }


def evidence_chain(hotspot, satellite_summary=None):
    from citizen_reports.models import CitizenReport

    since = timezone.now() - timezone.timedelta(minutes=60)
    n_recent = CitizenReport.objects.filter(hotspot=hotspot, created_at__gte=since).count()
    n_total = CitizenReport.objects.filter(hotspot=hotspot).count()
    history_similar = hotspot.city.history.filter(aqi__gte=hotspot.aqi * 0.65).count() if hotspot.city else 0
    rise = int(round((hotspot.pm25_change - 1) * 100))
    return [
        {"n": "01", "title": "Citizen observation", "value": f"{n_recent} reports", "detail": f"last 60 min · {n_total} linked in total", "label": DEMO},
        {"n": "02", "title": "Sensor anomaly", "value": f"PM2.5 +{rise}%", "detail": f"{hotspot.pm25_change}× within {hotspot.change_window_min} min", "label": DEMO},
        {"n": "03", "title": "Satellite observation", "value": satellite_summary or "Thermal anomaly", "detail": "Earth Engine-ready pipeline", "label": DEMO},
        {"n": "04", "title": "Weather", "value": f"Wind {hotspot.wind_dir} {hotspot.wind_speed:.0f} km/h", "detail": "Transport toward downwind area", "label": DEMO},
        {"n": "05", "title": "Historical pattern", "value": "Similar event detected" if history_similar else "No close analogue", "detail": f"{history_similar} comparable days in 90-day record", "label": DEMO},
        {"n": "06", "title": "AI assessment", "value": f"{hotspot.confidence}% confidence", "detail": "Multi-source fusion — not a confirmed attribution", "label": "AI ASSESSMENT"},
    ]
