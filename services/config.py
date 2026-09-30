"""Central view of which external integrations are configured.

Every service checks `is_configured(...)` and falls back to a clearly
labelled demo/mock implementation when credentials are absent.
"""
from django.conf import settings

LIVE = "LIVE DATA"
DEMO = "DEMO DATA"
SIMULATED = "SIMULATED PREDICTION"


def cfg(name: str) -> str:
    return (settings.INTEGRATIONS.get(name) or "").strip()


def is_configured(*names: str) -> bool:
    return all(cfg(n) for n in names)


def _module_available(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def service_status():
    """Status shown in the UI. Never returns secret values."""
    rows = [
        ("Gemini multimodal", is_configured("GEMINI_API_KEY"), "GEMINI_API_KEY"),
        ("Vertex AI forecasting", is_configured("VERTEX_PROJECT_ID", "VERTEX_ENDPOINT_ID") and _module_available("google.cloud.aiplatform"), "VERTEX_PROJECT_ID + VERTEX_ENDPOINT_ID"),
        ("Google Earth Engine", is_configured("EARTH_ENGINE_PROJECT") and _module_available("ee"), "EARTH_ENGINE_PROJECT"),
        ("Google Maps Platform", is_configured("GOOGLE_MAPS_API_KEY"), "GOOGLE_MAPS_API_KEY"),
        ("BigQuery", is_configured("BIGQUERY_PROJECT_ID") and _module_available("google.cloud.bigquery"), "BIGQUERY_PROJECT_ID"),
        ("Firebase", is_configured("FIREBASE_PROJECT_ID"), "FIREBASE_PROJECT_ID"),
        ("Cloud Translation", is_configured("GOOGLE_TRANSLATE_API_KEY"), "GOOGLE_TRANSLATE_API_KEY"),
        ("data.gov.in", is_configured("DATA_GOV_IN_API_KEY"), "DATA_GOV_IN_API_KEY"),
    ]
    return [
        {"name": n, "mode": "LIVE" if ok else "DEMO", "env": env}
        for n, ok, env in rows
    ]


def demo_mode() -> bool:
    return not any(s["mode"] == "LIVE" for s in service_status())
