from collections import defaultdict

from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from alerts.models import AuthorityAlert
from citizen_reports.models import CitizenReport
from pollution.models import Country, CrossBorderEvent, Hotspot, SensorReading
from services import earth_engine_service, vertex_service
from services.config import demo_mode, service_status
from services.intelligence import evidence_chain, latest_weather


def _hourly_mean(qs, field="aqi", hours=24):
    since = timezone.now() - timezone.timedelta(hours=hours)
    buckets = defaultdict(list)
    for ts, v in qs.filter(timestamp__gte=since).values_list("timestamp", field):
        buckets[ts.replace(minute=0, second=0, microsecond=0)].append(v)
    return [{"t": k.isoformat(), "v": round(sum(v) / len(v), 1)} for k, v in sorted(buckets.items())]


@api_view(["GET"])
def dashboard(request):
    active = Hotspot.objects.filter(is_active=True).select_related("city__country")
    agg = active.aggregate(a=Avg("aqi"), c=Avg("confidence"))
    metrics = [
        {"key": "aqi", "label": "AQI INDEX", "value": round(agg["a"] or 0), "sub": "Network mean · active hotspots", "tone": "warning"},
        {"key": "hotspots", "label": "ACTIVE HOTSPOTS", "value": active.count(), "sub": f"{active.filter(status='CRITICAL').count()} critical", "tone": "danger"},
        {"key": "predicted", "label": "PREDICTED EVENTS", "value": active.filter(predicted_event=True).count(), "sub": "Next 24 h · simulated", "tone": "accent"},
        {"key": "xborder", "label": "CROSS-BORDER RISKS", "value": f"{CrossBorderEvent.objects.count():02d}", "sub": "Federated demo", "tone": "info"},
        {"key": "reports", "label": "CITIZEN REPORTS", "value": f"{CitizenReport.objects.count():,}", "sub": "All time · demo", "tone": "info"},
        {"key": "confidence", "label": "AI CONFIDENCE", "value": f"{round(agg['c'] or 0)}%", "sub": "Mean multi-source", "tone": "success"},
    ]
    countries = []
    for c in Country.objects.all():
        qs = active.filter(city__country=c)
        countries.append({"code": c.code, "name": c.name, "hotspots": qs.count(),
                          "avg_aqi": round(qs.aggregate(a=Avg("aqi"))["a"] or 0), "lat": c.lat, "lng": c.lng})
    feed = []
    for r in CitizenReport.objects.select_related("city")[:6]:
        feed.append({"kind": "report", "title": f"Citizen report {r.code}", "text": f"{r.get_pollution_type_display()} · {r.location_label}", "t": r.created_at.isoformat()})
    for a in AuthorityAlert.objects.exclude(status="RESOLVED")[:5]:
        feed.append({"kind": "alert", "severity": a.severity, "title": f"{a.severity} · {a.code}", "text": a.location, "t": a.created_at.isoformat()})
    feed.sort(key=lambda x: x["t"], reverse=True)
    india = SensorReading.objects.filter(city__country__code="IN")
    return Response({
        "data_label": "DEMO DATA",
        "demo_mode": demo_mode(),
        "metrics": metrics,
        "top_hotspots": [h.to_dict() for h in active[:6]],
        "countries": countries,
        "activity": feed[:10],
        "trend": {"aqi": _hourly_mean(india, "aqi"), "pm25": _hourly_mean(india, "pm25")},
        "status_breakdown": {s: active.filter(status=s).count() for s in ("CRITICAL", "HIGH", "MODERATE", "LOW")},
        "generated_at": timezone.now().isoformat(),
    })


@api_view(["GET"])
def system_status(request):
    return Response({"demo_mode": demo_mode(), "services": service_status(), "time": timezone.now().isoformat()})


@api_view(["GET"])
def hotspot_list(request):
    qs = Hotspot.objects.filter(is_active=True).select_related("city__country")
    country = request.GET.get("country")
    status = request.GET.get("status")
    q = (request.GET.get("q") or "")[:64]
    if country:
        qs = qs.filter(city__country__code=country.upper()[:2])
    if status:
        qs = qs.filter(status=status.upper()[:10])
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(region__icontains=q) | Q(city__name__icontains=q))
    return Response({"data_label": "DEMO DATA", "count": qs.count(), "results": [h.to_dict() for h in qs]})


def hotspot_payload(h: Hotspot):
    d = h.to_dict()
    sat = earth_engine_service.get_observations(h.lat, h.lng, 15)
    d["downwind_label"] = next((r[7] for r in _hotspot_meta() if r[0] == h.code), None)
    movement = vertex_service.predict_pollution_movement({**d, "downwind_label": d["downwind_label"]})
    readings = list(h.readings.order_by("timestamp").values("timestamp", "pm25", "pm10", "aqi"))
    return {
        **d,
        "evidence": evidence_chain(h, sat["summary"]),
        "readings": [{"t": r["timestamp"].isoformat(), "pm25": r["pm25"], "pm10": r["pm10"], "aqi": r["aqi"]} for r in readings],
        "weather": latest_weather(h.city),
        "satellite": sat,
        "movement": movement,
        "reports": [r.to_dict() for r in h.reports.all()[:8]],
    }


def _hotspot_meta():
    from services.demo_data import HOTSPOTS
    return HOTSPOTS


@api_view(["GET"])
def hotspot_detail(request, code):
    h = get_object_or_404(Hotspot.objects.select_related("city__country"), code=code[:32])
    return Response(hotspot_payload(h))
