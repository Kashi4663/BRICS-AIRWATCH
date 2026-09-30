"""BigQuery-ready data architecture.

Schemas mirror the Django models so the local SQLite/demo data can be pushed
to BigQuery later with `python manage.py bigquery_sync` once
BIGQUERY_PROJECT_ID and google-cloud-bigquery are available.
"""
import logging

from .config import cfg, is_configured

log = logging.getLogger("airwatch")

S, F, I, T, B, J = "STRING", "FLOAT64", "INT64", "TIMESTAMP", "BOOL", "JSON"

SCHEMAS = {
    "citizen_reports": [("code", S), ("pollution_type", S), ("description", S), ("lat", F), ("lng", F), ("city", S),
                        ("hotspot", S), ("language", S), ("ai_label", S), ("ai_confidence", I), ("ai_source", S),
                        ("status", S), ("created_at", T), ("is_demo", B)],
    "sensor_readings": [("city", S), ("hotspot", S), ("timestamp", T), ("pm25", F), ("pm10", F), ("no2", F),
                        ("so2", F), ("co", F), ("aqi", I), ("is_demo", B)],
    "satellite_observations": [("hotspot", S), ("country", S), ("lat", F), ("lng", F), ("observed_at", T),
                               ("obs_type", S), ("intensity", F), ("confidence", I), ("source", S), ("is_demo", B)],
    "weather_observations": [("city", S), ("timestamp", T), ("temperature", F), ("humidity", F), ("wind_speed", F),
                             ("wind_deg", I), ("rainfall", F), ("is_demo", B)],
    "pollution_events": [("code", S), ("region", S), ("city", S), ("lat", F), ("lng", F), ("aqi", I), ("pm25", F),
                         ("status", S), ("confidence", I), ("source_category", S), ("sources", J), ("detected_at", T), ("is_demo", B)],
    "forecast_results": [("hotspot", S), ("city", S), ("generated_at", T), ("horizon_hours", I), ("aqi", I),
                         ("pm25", F), ("spike_probability", I), ("risk", S), ("confidence", I), ("model_source", S)],
    "authority_alerts": [("code", S), ("hotspot", S), ("severity", S), ("location", S), ("pollutant", S),
                         ("current_value", F), ("predicted_value", F), ("confidence", I), ("evidence", J),
                         ("status", S), ("created_at", T), ("is_demo", B)],
    "historical_aqi": [("city", S), ("date", "DATE"), ("aqi", I), ("pm25", F), ("pm10", F), ("fire_events", I), ("is_demo", B)],
}


def schema_json():
    return {t: [{"name": n, "type": ty, "mode": "NULLABLE"} for n, ty in cols] for t, cols in SCHEMAS.items()}


def is_live() -> bool:
    if not is_configured("BIGQUERY_PROJECT_ID"):
        return False
    try:
        from google.cloud import bigquery  # noqa: F401
        return True
    except Exception:
        return False


def insert_rows(table: str, rows: list[dict]):
    """Stream rows to BigQuery if configured; otherwise a no-op (data stays in Django DB)."""
    if not is_live():
        return {"mode": "LOCAL", "inserted": 0}
    from google.cloud import bigquery

    client = bigquery.Client(project=cfg("BIGQUERY_PROJECT_ID"))
    table_id = f"{cfg('BIGQUERY_PROJECT_ID')}.{cfg('BIGQUERY_DATASET') or 'airwatch'}.{table}"
    errors = client.insert_rows_json(table_id, rows)
    if errors:
        log.warning("BigQuery insert errors: %s", errors[:3])
    return {"mode": "BIGQUERY", "inserted": len(rows) - len(errors)}
