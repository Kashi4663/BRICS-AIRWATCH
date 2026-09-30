from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pollution.models import City, Hotspot
from services import vertex_service
from services.demo_data import KEY_CODE
from services.intelligence import latest_weather


@api_view(["GET"])
def forecast(request):
    code = (request.GET.get("hotspot") or KEY_CODE)[:32]
    city_name = request.GET.get("city")
    if city_name:
        city = get_object_or_404(City, name__iexact=city_name[:64])
        hotspot = city.hotspots.first()
        current = city.history.order_by("-date").values_list("aqi", flat=True).first() or city.base_aqi
        title = f"{city.name}, {city.country.name}"
    else:
        hotspot = get_object_or_404(Hotspot.objects.select_related("city"), code=code)
        city = hotspot.city
        current = 142 if hotspot.code == KEY_CODE else int(hotspot.aqi * 0.75)
        title = f"{hotspot.region}"
    w = latest_weather(city)
    features = {
        "current_aqi": current, "temperature": w.get("temperature", 31), "humidity": w.get("humidity", 48),
        "wind_speed": w.get("wind_speed", 12), "wind_direction": w.get("wind_deg", 200),
        "fire_events": city.history.order_by("-date").values_list("fire_events", flat=True).first() if city else 0,
        "citizen_reports": hotspot.citizen_report_count if hotspot else 0,
    }
    aq = vertex_service.predict_air_quality(features)
    spike = vertex_service.predict_pollution_spike(features)
    s = aq["series"]
    horizons = [{"label": "CURRENT", "h": 0, "aqi": s[0]["aqi"]}] + [
        {"label": f"+{h} HOURS", "h": h, "aqi": s[h]["aqi"]} for h in (6, 12, 24, 48)
    ]
    return Response({
        "title": title,
        "hotspot": hotspot.code if hotspot else None,
        "label": aq["label"],
        "model_source": aq["source"],
        "features_used": vertex_service.MODEL_FEATURES,
        "horizons": horizons,
        "series": s,
        "spike": spike,
        "cities": list(City.objects.values_list("name", flat=True)),
        "hotspots": list(Hotspot.objects.values_list("code", flat=True)),
    })
