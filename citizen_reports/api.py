import uuid

from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from citizen_reports.models import POLLUTION_TYPES, CitizenReport
from services import earth_engine_service, firebase_service, gemini_service, speech_service
from services.intelligence import latest_weather, nearby_context
from services.validators import clean_float, clean_text, validate_image

VALID_TYPES = {k for k, _ in POLLUTION_TYPES}
VALID_LANGS = {code for code, _, _ in speech_service.LANGUAGES}


class ReportView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = "reports"

    def get_throttles(self):
        # only throttle submissions, not listing
        return super().get_throttles() if self.request.method == "POST" else []

    def get(self, request):
        qs = CitizenReport.objects.select_related("city", "hotspot")
        status = request.GET.get("status")
        if status:
            qs = qs.filter(status=status.upper()[:24])
        total = qs.count()
        by_type = {k: qs.filter(pollution_type=k).count() for k in VALID_TYPES}
        return Response({"data_label": "DEMO DATA", "count": total, "by_type": by_type,
                         "results": [r.to_dict() for r in qs[:40]]})

    def post(self, request):
        d = request.data
        ptype = d.get("pollution_type", "unknown")
        if ptype not in VALID_TYPES:
            raise ValidationError({"pollution_type": "Invalid pollution type."})
        lang = d.get("language", "en")
        if lang not in VALID_LANGS:
            lang = "en"
        lat = clean_float(d.get("lat"), "lat", -90, 90)
        lng = clean_float(d.get("lng"), "lng", -180, 180)
        description = clean_text(d.get("description"), "description", 1000)
        transcript = clean_text(d.get("voice_transcript"), "voice_transcript", 2000)
        location_label = clean_text(d.get("location_label"), "location_label", 128)
        upload = request.FILES.get("image")
        image_bytes = validate_image(upload) if upload else b""

        nearby = nearby_context(lat, lng)
        hotspot = nearby.pop("nearest_hotspot_obj")
        city = hotspot.city if hotspot and nearby["distance_km"] is not None and nearby["distance_km"] < 60 else None
        weather = latest_weather(city) if city else {}
        satellite = earth_engine_service.get_observations(lat, lng, 25)
        translated = speech_service.translate(transcript or description, "en", lang) if (transcript or description) else {"text": ""}

        image_ai = gemini_service.analyze_pollution_image(
            image_bytes, upload.content_type if upload else "image/jpeg", ptype,
            {"description": translated["text"], "lat": lat, "lng": lng},
        )
        assessment = gemini_service.analyze_citizen_report({"type": ptype}, image_ai, weather, nearby, satellite)

        report = CitizenReport(
            code=f"CR-{uuid.uuid4().hex[:8].upper()}",
            user=request.user if request.user.is_authenticated else None,
            pollution_type=ptype, description=description, lat=lat, lng=lng,
            location_label=location_label or (hotspot.region if hotspot and city else "User location"),
            city=city, hotspot=hotspot if city and nearby["distance_km"] < 10 else None, language=lang,
            voice_transcript=transcript, translated_text=translated["text"],
            ai_category=image_ai["category"], ai_label=image_ai["label"], ai_confidence=assessment["confidence"],
            ai_indicators=image_ai["indicators"], ai_source=image_ai["source"], status="AWAITING_VERIFICATION", is_demo=False,
        )
        if upload:
            ext = upload.name.rsplit(".", 1)[-1].lower()
            upload.name = f"{report.code}.{ext}"  # never trust client file names
            report.image = upload
        report.save()
        if report.hotspot:
            report.hotspot.citizen_report_count = report.hotspot.reports.count()
            report.hotspot.save(update_fields=["citizen_report_count"])
        firebase_service.publish_report(report.to_dict())

        return Response({
            "report": report.to_dict(),
            "image_analysis": image_ai,
            "assessment": assessment,
            "weather": weather,
            "nearby": nearby,
            "satellite": {k: satellite[k] for k in ("count", "summary", "label")},
            "pipeline": ["ANALYZING IMAGE", "VERIFYING LOCATION", "CHECKING WEATHER", "CHECKING NEARBY OBSERVATIONS", "CROSS-REFERENCING SATELLITE DATA"],
        }, status=201)


class VoiceProcessView(APIView):
    """Speech-to-Text happens client-side; this runs Translation + Intent detection."""
    throttle_scope = "ai"
    parser_classes = [JSONParser, FormParser]

    def post(self, request):
        transcript = clean_text(request.data.get("transcript"), "transcript", 2000)
        lang = request.data.get("language", "en")
        if lang not in VALID_LANGS:
            lang = "en"
        if not transcript:
            raise ValidationError({"transcript": "Transcript is empty."})
        return Response(speech_service.process_voice_report(transcript, lang))
