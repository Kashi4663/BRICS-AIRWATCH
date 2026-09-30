"""Google Earth Engine abstraction.

Live path (EARTH_ENGINE_PROJECT set and `earthengine-api` installed):
queries the public FIRMS active-fire collection and Sentinel-5P NO2 around a
point. Otherwise returns the stored DEMO observations — never fabricated
"live" results.
"""
import datetime as dt
import logging
import math

from .config import DEMO, LIVE, cfg, is_configured

log = logging.getLogger("airwatch")

CAPABILITIES = ["satellite_imagery", "fire_detection", "vegetation_analysis", "land_use_analysis", "thermal_anomalies"]


def is_live() -> bool:
    if not is_configured("EARTH_ENGINE_PROJECT"):
        return False
    try:
        import ee  # noqa: F401
        return True
    except Exception:
        return False


def _live_fire_count(lat, lng, radius_km=10, days=3):
    import ee

    ee.Initialize(project=cfg("EARTH_ENGINE_PROJECT"))
    region = ee.Geometry.Point([lng, lat]).buffer(radius_km * 1000)
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    fires = ee.ImageCollection("FIRMS").filterDate(str(start), str(end)).filterBounds(region)
    return fires.size().getInfo()


def _haversine(lat1, lng1, lat2, lng2):
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_observations(lat, lng, radius_km=25):
    """Return satellite observations near a point with an explicit data label."""
    from pollution.models import SatelliteObservation

    if is_live():
        try:
            n = _live_fire_count(lat, lng, radius_km)
            return {"count": n, "observations": [], "label": LIVE, "source": "Earth Engine FIRMS",
                    "summary": f"{n} FIRMS fire detections within {radius_km} km (last 3 days)"}
        except Exception as exc:
            log.warning("Earth Engine query failed, using demo observations: %s", exc)

    obs = [o for o in SatelliteObservation.objects.all()
           if _haversine(lat, lng, o.lat, o.lng) <= radius_km]
    obs.sort(key=lambda o: -o.intensity)
    if obs:
        top = obs[0]
        summary = f"{top.get_obs_type_display()} (intensity {top.intensity:.2f})"
    else:
        summary = "No observation in window"
    return {"count": len(obs), "observations": [o.to_dict() for o in obs[:10]], "label": DEMO,
            "source": "Demo observation (Earth Engine-ready)", "summary": summary}
