"""Gemini multimodal service abstraction.

Uses the Gemini REST API (generativelanguage.googleapis.com) when
GEMINI_API_KEY is set. Otherwise a deterministic, clearly-labelled MOCK
service is used so the prototype runs with no credentials.

Every output is an *assessment*, never a confirmed fact.
"""
import base64
import json
import logging

import requests

from .config import cfg, is_configured

log = logging.getLogger("airwatch")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SOURCE_LIVE = "GEMINI"
SOURCE_MOCK = "MOCK AI (DEMO)"

MOCK_PROFILES = {
    "crop_burning": ("agricultural_burning", "Possible agricultural burning", 87, [
        "Low-altitude grey-white smoke layer over open terrain",
        "No stack or chimney structure visible",
        "Diffuse, horizontally spreading plume typical of biomass combustion",
    ]),
    "industrial": ("industrial_emission", "Possible industrial emission", 84, [
        "Elevated point-source plume",
        "Dark/brown plume colouration suggesting combustion by-products",
        "Built structures consistent with an industrial site",
    ]),
    "smoke": ("open_combustion", "Possible open combustion smoke", 81, [
        "Dense smoke column with visible vertical rise",
        "Reduced visibility around the source",
        "Grey colouration consistent with incomplete combustion",
    ]),
    "dust": ("dust", "Possible construction / road dust", 79, [
        "Brown-tan particulate haze close to ground level",
        "Disturbed soil or construction material visible",
        "No flame or combustion indicators",
    ]),
    "garbage_burning": ("waste_burning", "Possible open waste burning", 83, [
        "Small localised fire with dark smoke",
        "Mixed debris visible at ground level",
        "Plume colour consistent with plastic combustion",
    ]),
    "unknown": ("agricultural_burning", "Possible agricultural burning", 74, [
        "Smoke-like haze detected in frame",
        "Open landscape in background",
        "Source type ambiguous — additional evidence required",
    ]),
}


def is_live() -> bool:
    return is_configured("GEMINI_API_KEY")


def _call_gemini(parts, json_mode=True, timeout=30):
    model = cfg("GEMINI_MODEL") or "gemini-2.5-flash"
    body = {"contents": [{"role": "user", "parts": parts}]}
    if json_mode:
        body["generationConfig"] = {"responseMimeType": "application/json", "temperature": 0.2}
    resp = requests.post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": cfg("GEMINI_API_KEY"), "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text) if json_mode else text


# --------------------------------------------------------------------------
def analyze_pollution_image(image_bytes: bytes, mime_type: str = "image/jpeg", hint_type: str = "unknown", context: dict | None = None) -> dict:
    """Classify a citizen photo and extract visual pollution indicators."""
    if is_live() and image_bytes:
        prompt = (
            "You are an environmental analyst. Examine this citizen-submitted photo for air pollution. "
            "Return JSON with keys: category (one of agricultural_burning, industrial_emission, open_combustion, "
            "dust, waste_burning, vehicle_exhaust, no_pollution_visible), label (short phrase starting with 'Possible'), "
            "confidence (0-100 integer), indicators (list of 3 short visual observations), "
            "reasoning (one sentence). Never state the source as confirmed fact. "
            f"Citizen-selected type: {hint_type}. Context: {json.dumps(context or {})}"
        )
        try:
            out = _call_gemini([
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}},
            ])
            return {
                "category": out.get("category", "unknown"),
                "label": out.get("label", "Possible pollution event"),
                "confidence": int(out.get("confidence", 60)),
                "indicators": out.get("indicators", [])[:5],
                "reasoning": out.get("reasoning", ""),
                "source": SOURCE_LIVE,
            }
        except Exception as exc:  # fall back, but say so
            log.warning("Gemini image analysis failed, using mock: %s", exc)
            result = _mock_image(hint_type)
            result["note"] = "Gemini call failed — mock assessment shown."
            return result
    return _mock_image(hint_type)


def _mock_image(hint_type: str) -> dict:
    cat, label, conf, indicators = MOCK_PROFILES.get(hint_type, MOCK_PROFILES["unknown"])
    return {
        "category": cat,
        "label": label,
        "confidence": conf,
        "indicators": indicators,
        "reasoning": "Deterministic mock assessment based on the reported pollution type (GEMINI_API_KEY not configured).",
        "source": SOURCE_MOCK,
    }


def analyze_citizen_report(report: dict, image_analysis: dict, weather: dict, nearby: dict, satellite: dict) -> dict:
    """Fuse image assessment with location / weather / sensor / satellite context."""
    conf = image_analysis.get("confidence", 60)
    checks = []
    if nearby.get("reports_within_3km", 0) >= 3:
        checks.append({"label": "Nearby citizen observations", "value": f"{nearby['reports_within_3km']} within 3 km", "ok": True})
    else:
        checks.append({"label": "Nearby citizen observations", "value": f"{nearby.get('reports_within_3km', 0)} within 3 km", "ok": False})
    if nearby.get("nearest_hotspot"):
        checks.append({"label": "Nearest monitored hotspot", "value": f"{nearby['nearest_hotspot']} ({nearby['distance_km']} km)", "ok": nearby["distance_km"] < 25})
    checks.append({"label": "Weather", "value": f"Wind {weather.get('wind_dir', '—')} {weather.get('wind_speed', '—')} km/h, RH {weather.get('humidity', '—')}%", "ok": True})
    checks.append({"label": "Satellite observation", "value": satellite.get("summary", "No observation in window"), "ok": bool(satellite.get("count"))})
    conf = max(5, min(conf, 95))
    return {
        "label": image_analysis.get("label"),
        "confidence": conf,
        "status": "AWAITING_VERIFICATION",
        "status_label": "Awaiting multi-source verification",
        "checks": checks,
        "disclaimer": "AI assessment only. Source attribution is not confirmed and requires verification by the relevant authority.",
        "source": image_analysis.get("source"),
    }


def generate_event_summary(hotspot: dict, evidence: list) -> str:
    if is_live():
        try:
            return _call_gemini([{"text": (
                "Write a 3-sentence neutral situation summary for environmental authorities. Use cautious language "
                "('possible', 'indicates'); do not claim confirmed sources. Data (DEMO unless labelled LIVE): "
                + json.dumps({"hotspot": hotspot, "evidence": evidence})
            )}], json_mode=False)
        except Exception as exc:
            log.warning("Gemini summary failed: %s", exc)
    return (
        f"Hotspot {hotspot['code']} in {hotspot['region']} shows PM2.5 at {hotspot['pm25']} μg/m³, "
        f"a {hotspot['pm25_change']}× rise within {hotspot['change_window_min']} minutes. "
        f"Multiple independent signals point to a possible {hotspot['source_category'].lower()} event, "
        f"with winds from the {hotspot['wind_dir']} at {hotspot['wind_speed']} km/h likely carrying the plume downwind. "
        "This is an AI-generated assessment on demo data and requires authority verification."
    )


def investigate_hotspot(hotspot: dict, evidence: list, movement: dict) -> dict:
    fallback = {
        "headline": "Potential pollution event detected.",
        "findings": [
            f"PM2.5 increased {hotspot['pm25_change']}× within {hotspot['change_window_min']} minutes.",
            f"{hotspot['citizen_report_count']} citizen observations were reported within 3 km.",
            f"Meteorological conditions indicate movement toward {movement.get('toward', 'a downwind urban area')}.",
        ],
        "possible_sources": [
            {"category": hotspot["source_category"], "likelihood": "Most consistent with evidence"},
            {"category": "Vehicular / urban background", "likelihood": "Contributing, lower likelihood"},
        ],
        "confidence": min(95, max(40, hotspot["confidence"] - 2)),
        "status": "REQUIRES AUTHORITY VERIFICATION",
        "source": SOURCE_MOCK,
    }
    if is_live():
        try:
            out = _call_gemini([{"text": (
                "You are an AI pollution investigation agent. Given this multi-source evidence (demo data unless labelled), "
                "return JSON: headline (string), findings (list of 3-4 short evidence statements), "
                "possible_sources (list of {category, likelihood}), confidence (0-100 int). "
                "Use hedged language; never state a confirmed polluter. Data: "
                + json.dumps({"hotspot": hotspot, "evidence": evidence, "movement": movement})
            )}])
            fallback.update({k: out[k] for k in ("headline", "findings", "possible_sources", "confidence") if k in out})
            fallback["source"] = SOURCE_LIVE
        except Exception as exc:
            log.warning("Gemini investigation failed: %s", exc)
    fallback["status"] = "REQUIRES AUTHORITY VERIFICATION"
    return fallback


def assistant_reply(question: str, context: dict) -> dict | None:
    """Live Gemini answer grounded in the app's data. Returns None when not configured."""
    if not is_live():
        return None
    try:
        text = _call_gemini([{"text": (
            "You are AIRWATCH AI, assistant for a climate intelligence prototype. Answer concisely (max 120 words) "
            "using ONLY the JSON context. The data is DEMO/synthetic unless labelled LIVE — say so when relevant. "
            "Never present AI conclusions as confirmed facts.\nContext: " + json.dumps(context, default=str)
            + "\nQuestion: " + question
        )}], json_mode=False)
        return {"answer": text, "source": SOURCE_LIVE}
    except Exception as exc:
        log.warning("Gemini assistant failed: %s", exc)
        return None
