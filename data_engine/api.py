import datetime as dt
from collections import Counter, defaultdict

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from citizen_reports.models import CitizenReport
from pollution.models import City, Country, HistoricalAQI, Hotspot
from services.bigquery_service import SCHEMAS, is_live as bq_live


def _int(v, default, lo, hi):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


@api_view(["GET"])
def data_explorer(request):
    g = request.GET
    country = (g.get("country") or "IN").upper()[:2]
    city = (g.get("city") or "")[:64]
    days = _int(g.get("days"), 30, 7, 90)
    pollutant = g.get("pollutant") if g.get("pollutant") in ("aqi", "pm25", "pm10") else "aqi"
    min_conf = _int(g.get("confidence"), 0, 0, 100)
    source = (g.get("source") or "")[:40]
    event_type = (g.get("event_type") or "").upper()[:10]

    since = timezone.localdate() - dt.timedelta(days=days)
    cities = City.objects.filter(country__code=country) if country != "AL" else City.objects.all()
    if city:
        cities = cities.filter(name__iexact=city)
    hist = HistoricalAQI.objects.filter(city__in=cities, date__gte=since).select_related("city")

    series = defaultdict(list)
    fires = defaultdict(int)
    scatter = []
    for r in hist:
        series[r.city.name].append({"d": r.date.isoformat(), "v": getattr(r, pollutant)})
        fires[r.date.isoformat()] += r.fire_events
        scatter.append({"x": r.wind_speed, "y": r.aqi, "city": r.city.name})
    top_cities = sorted(series, key=lambda k: -sum(p["v"] for p in series[k]))[:6]

    rep = CitizenReport.objects.filter(city__in=cities, created_at__gte=timezone.now() - dt.timedelta(days=days))
    per_day = Counter(r.date().isoformat() for r in rep.values_list("created_at", flat=True))
    by_type = Counter(rep.values_list("pollution_type", flat=True))

    events = Hotspot.objects.filter(city__in=cities, confidence__gte=min_conf).select_related("city__country")
    if source:
        events = events.filter(source_category__icontains=source)
    if event_type in ("CRITICAL", "HIGH", "MODERATE", "LOW"):
        events = events.filter(status=event_type)

    return Response({
        "data_label": "DEMO DATA",
        "storage": "BigQuery" if bq_live() else "Django DB (BigQuery-ready schema)",
        "filters": {"country": country, "city": city, "days": days, "pollutant": pollutant, "confidence": min_conf, "source": source, "event_type": event_type},
        "options": {
            "countries": [{"code": c.code, "name": c.name} for c in Country.objects.all()],
            "cities": list(City.objects.filter(country__code=country).values_list("name", flat=True)) if country != "AL" else list(City.objects.values_list("name", flat=True)),
        },
        "trends": {k: series[k] for k in top_cities},
        "fires": [{"d": k, "v": v} for k, v in sorted(fires.items())],
        "reports_per_day": [{"d": k, "v": v} for k, v in sorted(per_day.items())],
        "reports_by_type": dict(by_type),
        "weather_correlation": scatter[:600],
        "events": [h.to_dict() for h in events],
        "tables": list(SCHEMAS.keys()),
    })
