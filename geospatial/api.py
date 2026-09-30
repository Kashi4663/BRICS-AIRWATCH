"""Geospatial endpoints: map layers and cross-border intelligence."""
import math

from django.db.models import Avg
from rest_framework.decorators import api_view
from rest_framework.response import Response

from citizen_reports.models import CitizenReport
from pollution.models import Country, CrossBorderEvent, Hotspot, IndustrialZone, SatelliteObservation
from services import vertex_service
from services.config import cfg
from services.demo_data import HOTSPOTS


def _wind_grid(hotspots):
    """Coarse wind vectors around each hotspot (demo meteorology)."""
    grid = []
    for h in hotspots:
        for dx, dy in ((-0.25, -0.25), (0.25, -0.25), (-0.25, 0.25), (0.25, 0.25), (0, 0.4)):
            grid.append({"lat": round(h.lat + dy, 3), "lng": round(h.lng + dx, 3),
                         "deg": (h.wind_deg + int(8 * math.sin(dx * 20 + dy * 13))) % 360, "speed": h.wind_speed})
    return grid


@api_view(["GET"])
def map_layers(request):
    hotspots = list(Hotspot.objects.filter(is_active=True).select_related("city__country"))
    downwind = {r[0]: r[7] for r in HOTSPOTS}
    predictions = []
    for h in hotspots:
        if h.predicted_event:
            d = h.to_dict()
            d["downwind_label"] = downwind.get(h.code)
            mv = vertex_service.predict_pollution_movement(d)
            predictions.append({"code": h.code, "path": mv["path"], "heading": mv["heading"], "label": mv["label"]})
    reports = CitizenReport.objects.only("code", "lat", "lng", "pollution_type", "status", "created_at")[:400]
    return Response({
        "data_label": "DEMO DATA",
        "map_provider": "google" if cfg("GOOGLE_MAPS_API_KEY") else "leaflet-carto",
        "hotspots": [h.to_dict() for h in hotspots],
        "reports": [{"code": r.code, "lat": r.lat, "lng": r.lng, "type": r.pollution_type, "status": r.status} for r in reports],
        "industrial": [{"name": z.name, "lat": z.lat, "lng": z.lng, "sector": z.sector} for z in IndustrialZone.objects.all()],
        "fires": [s.to_dict() for s in SatelliteObservation.objects.filter(obs_type="fire")],
        "satellite": [s.to_dict() for s in SatelliteObservation.objects.exclude(obs_type="fire")],
        "wind": _wind_grid(hotspots),
        "predictions": predictions,
    })


@api_view(["GET"])
def cross_border(request):
    rows = []
    for c in Country.objects.all():
        hs = Hotspot.objects.filter(city__country=c, is_active=True)
        out = CrossBorderEvent.objects.filter(origin_country=c).count()
        inc = CrossBorderEvent.objects.filter(affected_country=c).count()
        rows.append({
            "code": c.code, "name": c.name, "lat": c.lat, "lng": c.lng,
            "active_events": hs.count(), "predicted_events": hs.filter(predicted_event=True).count(),
            "avg_aqi": round(hs.aggregate(a=Avg("aqi"))["a"] or 0),
            "shared_model_status": c.shared_model_status, "model_version": c.model_version,
            "cross_border_risk": "HIGH" if out + inc >= 2 else "MODERATE" if out + inc == 1 else "LOW",
        })
    return Response({
        "label": "FEDERATED ARCHITECTURE DEMONSTRATION",
        "disclaimer": "This prototype does not exchange data between BRICS countries. All country data, models and trajectories are simulated.",
        "countries": rows,
        "events": [e.to_dict() for e in CrossBorderEvent.objects.select_related("origin_country", "affected_country")],
    })
