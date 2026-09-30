"""AI endpoints: image analysis, investigation agent, assistant."""
import re

from django.db.models import Avg
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from alerts.models import AuthorityAlert
from citizen_reports.models import POLLUTION_TYPES, CitizenReport
from pollution.api import hotspot_payload
from pollution.models import CrossBorderEvent, Hotspot
from services import firebase_service, gemini_service, vertex_service
from services.demo_data import KEY_CODE
from services.validators import clean_text, validate_image

VALID_TYPES = {k for k, _ in POLLUTION_TYPES}


class AnalyzeImageView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "ai"

    def post(self, request):
        upload = request.FILES.get("image")
        if not upload:
            raise ValidationError({"image": "Image is required."})
        data = validate_image(upload)
        ptype = request.data.get("pollution_type", "unknown")
        if ptype not in VALID_TYPES:
            ptype = "unknown"
        return Response(gemini_service.analyze_pollution_image(data, upload.content_type, ptype))


class InvestigateView(APIView):
    """AI investigation agent: gathers multi-source evidence, then produces a hedged assessment."""
    throttle_scope = "ai"
    parser_classes = [JSONParser, FormParser]

    def post(self, request):
        code = str(request.data.get("hotspot") or KEY_CODE)[:32]
        h = get_object_or_404(Hotspot.objects.select_related("city__country"), code=code)
        p = hotspot_payload(h)
        n_reports = CitizenReport.objects.filter(hotspot=h).count()
        steps = [
            {"id": 1, "label": "Sensor data retrieved", "detail": f"{len(p['readings'])} readings · PM2.5 {p['pm25']} μg/m³"},
            {"id": 2, "label": f"{n_reports} citizen reports analyzed", "detail": f"{p['evidence'][0]['value']} in the last 60 min"},
            {"id": 3, "label": "Weather conditions checked", "detail": f"Wind {p['wind_dir']} {p['wind_speed']} km/h, RH {p['weather'].get('humidity', '—')}%"},
            {"id": 4, "label": "Satellite observation checked", "detail": f"{p['satellite']['summary']} [{p['satellite']['label']}]"},
            {"id": 5, "label": "Historical pattern analyzed", "detail": p["evidence"][4]["detail"]},
            {"id": 6, "label": "Possible source categories determined", "detail": p["source_category"]},
            {"id": 7, "label": "Wind trajectory calculated", "detail": f"Heading {p['movement']['heading']} toward {p['movement']['toward']}"},
            {"id": 8, "label": "Confidence assessment generated", "detail": "Multi-source fusion"},
            {"id": 9, "label": "Investigation report created", "detail": "Pending authority verification"},
        ]
        result = gemini_service.investigate_hotspot(p, p["evidence"], p["movement"])
        summary = gemini_service.generate_event_summary(p, p["evidence"])
        features = {"current_aqi": 142 if h.code == KEY_CODE else int(h.aqi * 0.75), "wind_speed": h.wind_speed}
        spike = vertex_service.predict_pollution_spike(features)

        alert = AuthorityAlert.objects.filter(hotspot=h).exclude(status="RESOLVED").first()
        created = False
        if alert is None and request.data.get("generate_alert", True) and h.status in ("CRITICAL", "HIGH"):
            last = AuthorityAlert.objects.order_by("-id").first()
            alert = AuthorityAlert.objects.create(
                code=f"AL-0926-{(last.id + 1) if last else 1:03d}", hotspot=h,
                severity="CRITICAL" if h.status == "CRITICAL" else "HIGH", title=f"{h.status} POLLUTION EVENT",
                location=h.region, pollutant=h.primary_pollutant, current_value=h.pm25, predicted_value=h.predicted_pm25,
                confidence=result["confidence"], evidence=["Sensor anomaly", "Citizen reports", "Satellite observation", "Wind trajectory"],
                origin="AI investigation agent (unverified)", is_demo=True,
            )
            firebase_service.notify_authorities(alert.to_dict())
            created = True
        return Response({
            "hotspot": {k: p[k] for k in ("code", "region", "country", "lat", "lng", "pm25", "predicted_pm25", "aqi", "status", "confidence", "sources", "source_category", "wind_dir", "wind_speed")},
            "steps": steps,
            "result": result,
            "summary": summary,
            "evidence": p["evidence"],
            "movement": p["movement"],
            "readings": p["readings"],
            "spike": spike,
            "alert": {**alert.to_dict(), "created_now": created} if alert else None,
            "disclaimer": "AI-generated assessment on demo data. Not a confirmed finding or an official alert.",
        })


class AssistantView(APIView):
    throttle_scope = "ai"
    parser_classes = [JSONParser, FormParser]

    def post(self, request):
        q = clean_text(request.data.get("message"), "message", 500)
        if not q:
            raise ValidationError({"message": "Message is empty."})
        ctx = _context()
        live = gemini_service.assistant_reply(q, ctx)
        if live:
            return Response({**live, "label": "GEMINI"})
        return Response({"answer": _mock_answer(q, ctx), "source": "MOCK AI (DEMO)", "label": "DEMO DATA"})


def _context():
    active = Hotspot.objects.filter(is_active=True).select_related("city__country")
    return {
        "data_label": "DEMO DATA",
        "hotspots": [{k: h.to_dict()[k] for k in ("code", "region", "country", "aqi", "pm25", "predicted_pm25", "status", "confidence", "source_category", "wind_dir", "predicted_event")} for h in active[:15]],
        "open_alerts": [a.to_dict() for a in AuthorityAlert.objects.exclude(status="RESOLVED")[:8]],
        "cross_border": [e.to_dict() for e in CrossBorderEvent.objects.select_related("origin_country", "affected_country")],
        "active_count": active.count(),
        "mean_aqi": round(active.aggregate(a=Avg("aqi"))["a"] or 0),
        "citizen_reports": CitizenReport.objects.count(),
    }


def _mock_answer(q, ctx):
    ql = q.lower()
    hs = ctx["hotspots"]
    if re.search(r"spike|forecast|expected|predict", ql):
        pred = [h for h in hs if h["predicted_event"]][:5]
        lines = "; ".join(f"{h['region']} (PM2.5 {h['pm25']} → {h['predicted_pm25']} μg/m³)" for h in pred)
        return f"Simulated forecast flags {len([h for h in hs if h['predicted_event']])} areas for an AQI spike in the next 24 h. Highest: {lines}. For {KEY_CODE}, spike probability is 72% at 6 h, 84% at 12 h and 91% at 24 h. [SIMULATED PREDICTION]"
    if re.search(r"why|cause|increase|reason", ql):
        k = next((h for h in hs if h["code"] == KEY_CODE), hs[0])
        return (f"At {k['code']} ({k['region']}) PM2.5 rose 2.8× within 45 minutes to {k['pm25']} μg/m³. Evidence: a sensor anomaly, 7 citizen reports in the last hour within 3 km, "
                f"a demo thermal anomaly observation, and {k['wind_dir']} winds at 18 km/h carrying the plume toward the Bharuch urban area. The pattern is most consistent with a possible "
                f"{k['source_category'].lower()}, at {k['confidence']}% confidence. This is not a confirmed attribution and requires authority verification. [DEMO DATA]")
    if re.search(r"corridor|border|cross", ql):
        ev = ctx["cross_border"]
        lines = "; ".join(f"{e['code']}: {e['origin']} → {e['affected']} via {e['corridor']} ({e['direction']}, {e['window']}, {e['confidence']}%)" for e in ev)
        return f"{len(ev)} simulated cross-border / corridor events: {lines}. These are part of the federated architecture demonstration — no real data is exchanged between countries."
    if re.search(r"summar|today|anomal|overview", ql):
        crit = [h for h in hs if h["status"] == "CRITICAL"]
        return (f"Today's demo summary: {ctx['active_count']} active hotspots tracked, network mean AQI {ctx['mean_aqi']}. {len(crit)} are critical, led by {crit[0]['region'] if crit else '—'}. "
                f"{len(ctx['open_alerts'])} alerts await authority review and {ctx['citizen_reports']:,} citizen reports are in the system. The main anomaly is a 2.8× PM2.5 jump at {KEY_CODE} in the Gujarat Industrial Corridor. [DEMO DATA]")
    if re.search(r"hotspot|active|where|worst", ql) or True:
        top = hs[:5]
        lines = "; ".join(f"{h['code']} {h['region']} — AQI {h['aqi']} ({h['status']})" for h in top)
        return f"{ctx['active_count']} hotspots are active. Top 5 by AQI: {lines}. [DEMO DATA]"
