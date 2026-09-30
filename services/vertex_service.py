"""Vertex AI forecasting abstraction.

Live path: a deployed Vertex AI endpoint (VERTEX_PROJECT_ID, VERTEX_LOCATION,
VERTEX_ENDPOINT_ID) receiving the feature vector below and returning
{aqi_forecast: [...], spike_probability: {...}, risk, confidence}.

Fallback: a deterministic mock model. Output is labelled SIMULATED PREDICTION.
"""
import logging
import math

from .config import SIMULATED, cfg, is_configured

log = logging.getLogger("airwatch")

MODEL_FEATURES = [
    "historical_aqi", "pm25", "pm10", "wind_speed", "wind_direction", "temperature",
    "humidity", "rainfall", "satellite_observations", "fire_events", "citizen_reports", "industrial_indicators",
]

# Reference trajectory for the demo scenario (current 142 -> +24h 221)
_ANCHORS = [(0, 142), (6, 168), (12, 193), (24, 221), (36, 212), (48, 196)]
_SPIKE = {6: 72, 12: 84, 24: 91, 48: 78}

COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def is_live() -> bool:
    if not is_configured("VERTEX_PROJECT_ID", "VERTEX_ENDPOINT_ID"):
        return False
    try:
        import google.cloud.aiplatform  # noqa: F401
        return True
    except Exception:
        return False


def _interp(h):
    for (h0, v0), (h1, v1) in zip(_ANCHORS, _ANCHORS[1:]):
        if h0 <= h <= h1:
            return v0 + (v1 - v0) * (h - h0) / (h1 - h0)
    return _ANCHORS[-1][1]


def _risk(aqi):
    if aqi >= 200:
        return "CRITICAL"
    if aqi >= 150:
        return "HIGH"
    if aqi >= 100:
        return "MODERATE"
    return "LOW"


def _vertex_predict(features: dict):
    from google.cloud import aiplatform

    aiplatform.init(project=cfg("VERTEX_PROJECT_ID"), location=cfg("VERTEX_LOCATION") or "asia-south1")
    endpoint = aiplatform.Endpoint(cfg("VERTEX_ENDPOINT_ID"))
    return endpoint.predict(instances=[features]).predictions[0]


def predict_air_quality(features: dict, hours: int = 48) -> dict:
    """Hourly forecast series. `features` must include current_aqi and base weather."""
    if is_live():
        try:
            pred = _vertex_predict(features)
            return {"series": pred["series"], "source": "VERTEX AI", "label": "LIVE MODEL OUTPUT"}
        except Exception as exc:
            log.warning("Vertex prediction failed, using simulation: %s", exc)

    scale = features.get("current_aqi", 142) / 142.0
    t0 = features.get("temperature", 31)
    h0 = features.get("humidity", 48)
    w0 = features.get("wind_speed", 12)
    series = []
    for h in range(hours + 1):
        diurnal = math.sin((h + 6) / 24 * 2 * math.pi)
        aqi = _interp(h) * scale + (0 if h in (0, 6, 12, 24, 48) else 4 * math.sin(h * 1.7))
        series.append({
            "h": h,
            "aqi": round(aqi),
            "pm25": round(aqi * 0.62 + 3 * math.cos(h), 1),
            "pm10": round(aqi * 0.95 + 5 * math.sin(h / 2), 1),
            "temperature": round(t0 + 4.5 * diurnal, 1),
            "humidity": round(max(15, min(95, h0 - 12 * diurnal)), 1),
            "wind_speed": round(max(2, w0 - 3 * math.sin(h / 5) - h * 0.05), 1),
        })
    return {"series": series, "source": "MOCK MODEL", "label": SIMULATED}


def predict_pollution_spike(features: dict) -> dict:
    scale = features.get("current_aqi", 142) / 142.0
    probs = {k: int(max(5, min(97, v * (0.75 + 0.25 * scale)))) for k, v in _SPIKE.items()}
    return {
        "probabilities": [{"horizon": f"{k} HOURS", "hours": k, "probability": v} for k, v in probs.items()],
        "risk": _risk(_interp(24) * scale),
        "confidence": 86,
        "label": SIMULATED,
        "source": "VERTEX AI" if is_live() else "MOCK MODEL",
    }


def predict_pollution_movement(hotspot: dict, hours=(3, 6, 9, 12)) -> dict:
    """Simple advection projection along the wind vector (transport direction = wind_deg + 180)."""
    lat, lng = hotspot["lat"], hotspot["lng"]
    speed = hotspot.get("wind_speed", 12)
    # wind_deg is the direction the wind comes FROM; pollution travels the opposite way
    bearing = math.radians((hotspot.get("wind_deg", 45) + 180) % 360)
    path = [{"h": 0, "lat": lat, "lng": lng, "radius_km": 3}]
    for h in hours:
        dist_km = speed * h * 0.55  # dispersion-damped transport
        dlat = dist_km * math.cos(bearing) / 111.0
        dlng = dist_km * math.sin(bearing) / (111.0 * max(0.2, math.cos(math.radians(lat))))
        path.append({"h": h, "lat": round(lat + dlat, 4), "lng": round(lng + dlng, 4), "radius_km": round(3 + dist_km * 0.35, 1)})
    heading = COMPASS[int(((math.degrees(bearing) % 360) + 22.5) // 45) % 8]
    return {
        "path": path,
        "heading": heading,
        "toward": hotspot.get("downwind_label") or "a downwind urban area",
        "label": SIMULATED,
    }
