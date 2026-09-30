"""Synthetic DEMO dataset for BRICS AIRWATCH.

All values generated here are synthetic and flagged is_demo=True. They are
NOT official government measurements.
"""
import datetime as dt
import math
import random

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .intelligence import aqi_status

COUNTRIES = [
    ("IN", "India", 22.0, 79.0, "LOCAL MODEL · SIMULATED SYNC", "v0.9-demo"),
    ("BR", "Brazil", -10.0, -52.0, "LOCAL MODEL · SIMULATED SYNC", "v0.6-demo"),
    ("RU", "Russia", 60.0, 90.0, "LOCAL MODEL · SIMULATED SYNC", "v0.5-demo"),
    ("CN", "China", 34.0, 104.0, "LOCAL MODEL · SIMULATED SYNC", "v0.7-demo"),
    ("ZA", "South Africa", -29.0, 24.0, "LOCAL MODEL · SIMULATED SYNC", "v0.5-demo"),
]

# (country, name, state, lat, lng, base_aqi, industrial)
CITIES = [
    ("IN", "Ahmedabad", "Gujarat", 23.0225, 72.5714, 165, True),
    ("IN", "Rajkot", "Gujarat", 22.3039, 70.8022, 142, True),
    ("IN", "Ankleshwar", "Gujarat", 21.6264, 73.0152, 190, True),
    ("IN", "Vapi", "Gujarat", 20.3893, 72.9106, 178, True),
    ("IN", "Surat", "Gujarat", 21.1702, 72.8311, 150, True),
    ("IN", "Delhi", "Delhi", 28.6139, 77.2090, 236, False),
    ("IN", "Mumbai", "Maharashtra", 19.0760, 72.8777, 128, False),
    ("IN", "Bengaluru", "Karnataka", 12.9716, 77.5946, 92, False),
    ("IN", "Kolkata", "West Bengal", 22.5726, 88.3639, 158, False),
    ("IN", "Hyderabad", "Telangana", 17.3850, 78.4867, 118, False),
    ("IN", "Ludhiana", "Punjab", 30.9010, 75.8573, 205, True),
    ("IN", "Kanpur", "Uttar Pradesh", 26.4499, 80.3319, 214, True),
    ("BR", "São Paulo", "SP", -23.5505, -46.6333, 88, True),
    ("BR", "Manaus", "AM", -3.1190, -60.0217, 96, False),
    ("BR", "Porto Velho", "RO", -8.7612, -63.9004, 148, False),
    ("RU", "Moscow", "Moscow", 55.7558, 37.6173, 72, False),
    ("RU", "Norilsk", "Krasnoyarsk Krai", 69.3558, 88.1893, 132, True),
    ("RU", "Chelyabinsk", "Chelyabinsk Oblast", 55.1644, 61.4368, 118, True),
    ("RU", "Blagoveshchensk", "Amur Oblast", 50.2907, 127.5272, 84, False),
    ("CN", "Beijing", "Beijing", 39.9042, 116.4074, 128, False),
    ("CN", "Shijiazhuang", "Hebei", 38.0428, 114.5149, 172, True),
    ("CN", "Chengdu", "Sichuan", 30.5728, 104.0668, 121, False),
    ("CN", "Heihe", "Heilongjiang", 50.2455, 127.4889, 76, False),
    ("ZA", "Johannesburg", "Gauteng", -26.2041, 28.0473, 96, False),
    ("ZA", "Emalahleni", "Mpumalanga", -25.8713, 29.2332, 152, True),
    ("ZA", "Cape Town", "Western Cape", -33.9249, 18.4241, 58, False),
]

KEY_CODE = "IN-GJ-0926-018"
ALL_SOURCES = ["Citizen Reports", "Sensor Data", "Satellite Observation", "Meteorological Data"]

# (code, city, region, dlat, dlng, source_category, wind_deg, downwind)
HOTSPOTS = [
    (KEY_CODE, "Ankleshwar", "Gujarat Industrial Corridor — Ankleshwar", 0.0, 0.0, "Industrial emission", 200, "Bharuch urban area"),
    ("IN-GJ-0926-011", "Vapi", "Vapi GIDC Industrial Estate", 0.012, 0.02, "Industrial emission", 225, "Vapi town"),
    ("IN-GJ-0926-004", "Ahmedabad", "Ahmedabad — Vatva GIDC", -0.07, 0.06, "Industrial emission", 250, "Maninagar"),
    ("IN-GJ-0926-007", "Ahmedabad", "Ahmedabad — Naroda", 0.05, 0.09, "Mixed urban / industrial", 240, "Naroda residential belt"),
    ("IN-GJ-0926-022", "Rajkot", "Rajkot — Aji GIDC", 0.01, 0.04, "Industrial emission", 260, "Rajkot east"),
    ("IN-GJ-0926-015", "Surat", "Surat — Sachin GIDC", -0.08, -0.03, "Industrial emission", 230, "Surat south"),
    ("IN-DL-0926-003", "Delhi", "Delhi — Anand Vihar", 0.03, 0.10, "Vehicular + dust", 300, "East Delhi"),
    ("IN-DL-0926-009", "Delhi", "Delhi — Bawana", 0.18, -0.14, "Mixed urban / industrial", 310, "North-west Delhi"),
    ("IN-DL-0926-012", "Delhi", "Delhi — Okhla", -0.07, 0.07, "Waste burning", 290, "South-east Delhi"),
    ("IN-PB-0926-002", "Ludhiana", "Ludhiana rural belt", 0.08, 0.20, "Agricultural burning", 300, "Ludhiana city"),
    ("IN-PB-0926-005", "Ludhiana", "Sangrur agricultural district", -0.66, 0.0, "Agricultural burning", 310, "Patiala"),
    ("IN-UP-0926-006", "Kanpur", "Kanpur — Panki", 0.02, -0.08, "Industrial emission", 280, "Kanpur central"),
    ("IN-MH-0926-010", "Mumbai", "Mumbai — Chembur / Trombay", 0.0, 0.02, "Industrial emission", 270, "Chembur residential"),
    ("IN-WB-0926-008", "Kolkata", "Howrah industrial belt", 0.02, -0.05, "Mixed urban / industrial", 200, "Kolkata central"),
    ("IN-TG-0926-013", "Hyderabad", "Patancheru industrial area", 0.14, -0.23, "Industrial emission", 250, "Hyderabad west"),
    ("IN-KA-0926-016", "Bengaluru", "Peenya industrial area", 0.06, -0.08, "Construction dust", 250, "Yeshwanthpur"),
    ("BR-RO-0926-001", "Porto Velho", "Rondônia forest frontier", 0.3, 0.4, "Biomass / forest fire", 90, "Porto Velho"),
    ("BR-AM-0926-002", "Manaus", "Amazonas — south of Manaus", -0.6, 0.2, "Biomass / forest fire", 110, "Manaus"),
    ("BR-SP-0926-003", "São Paulo", "Cubatão industrial pole", -0.34, -0.05, "Industrial emission", 160, "São Paulo south"),
    ("RU-KK-0926-001", "Norilsk", "Norilsk smelter district", 0.0, 0.05, "Industrial emission (SO2)", 270, "Norilsk"),
    ("RU-CH-0926-002", "Chelyabinsk", "Chelyabinsk metallurgical zone", 0.03, 0.05, "Industrial emission", 250, "Chelyabinsk centre"),
    ("RU-AM-0926-003", "Blagoveshchensk", "Amur agricultural belt", 0.2, 0.1, "Agricultural burning", 320, "Blagoveshchensk"),
    ("CN-HE-0926-001", "Shijiazhuang", "Hebei industrial cluster", 0.05, 0.07, "Industrial emission", 200, "Shijiazhuang"),
    ("CN-BJ-0926-002", "Beijing", "Beijing — south-east", -0.10, 0.18, "Mixed urban / industrial", 190, "Beijing central"),
    ("CN-SC-0926-003", "Chengdu", "Chengdu basin", 0.05, -0.1, "Mixed urban / industrial", 20, "Chengdu"),
    ("ZA-MP-0926-001", "Emalahleni", "Mpumalanga coal belt", 0.05, 0.1, "Coal combustion", 60, "Emalahleni"),
    ("ZA-GP-0926-002", "Johannesburg", "Vaal Triangle", -0.9, -0.1, "Industrial emission", 30, "Johannesburg south"),
]

INDUSTRIAL_ZONES = [
    ("IN", "Ankleshwar GIDC", 21.61, 73.03, "Chemicals"), ("IN", "Dahej PCPIR", 21.71, 72.58, "Petrochemicals"),
    ("IN", "Vapi GIDC", 20.40, 72.93, "Chemicals"), ("IN", "Vatva GIDC", 22.96, 72.63, "Chemicals / dyes"),
    ("IN", "Aji GIDC Rajkot", 22.31, 70.84, "Engineering"), ("IN", "Sachin GIDC", 21.09, 72.80, "Textiles"),
    ("IN", "Panki Kanpur", 26.47, 80.25, "Power / tanneries"), ("IN", "Patancheru", 17.53, 78.26, "Pharmaceuticals"),
    ("IN", "Trombay", 19.00, 72.90, "Refining"), ("BR", "Cubatão", -23.89, -46.42, "Petrochemicals"),
    ("RU", "Norilsk Nickel", 69.35, 88.20, "Smelting"), ("RU", "Chelyabinsk Metallurgical", 55.25, 61.40, "Steel"),
    ("CN", "Hebei steel cluster", 38.10, 114.60, "Steel"), ("ZA", "Secunda", -26.52, 29.17, "Coal-to-liquids"),
    ("ZA", "Vanderbijlpark", -26.70, 27.85, "Steel"),
]

VOICES = [
    "Heavy smoke from fields near the highway", "Strong chemical smell and haze near GIDC", "Dust from construction site",
    "Garbage burning near the market", "Black smoke from chimney since morning", "Visibility reduced, eyes burning",
    "Smoke plume moving towards residential area", "Open burning of plastic waste",
]
TYPES = ["smoke", "dust", "industrial", "crop_burning", "garbage_burning", "unknown"]
TYPE_LABEL = {"smoke": "Possible open combustion smoke", "dust": "Possible construction / road dust",
              "industrial": "Possible industrial emission", "crop_burning": "Possible agricultural burning",
              "garbage_burning": "Possible open waste burning", "unknown": "Unclassified haze"}


def _pm_from_aqi(aqi):
    # rough inverse of the NAQI PM2.5 sub-index
    if aqi <= 100:
        return aqi * 0.6
    if aqi <= 200:
        return 60 + (aqi - 100) * 0.3
    if aqi <= 300:
        return 90 + (aqi - 200) * 0.3
    return 120 + (aqi - 300) * 1.3


@transaction.atomic
def seed(reset=False, stdout=None):
    from alerts.models import AuditLog, AuthorityAlert
    from citizen_reports.models import CitizenReport
    from dashboard.models import Profile
    from forecasting.models import ForecastResult
    from pollution.models import (City, Country, CrossBorderEvent, HistoricalAQI, Hotspot, IndustrialZone,
                                  SatelliteObservation, SensorReading, WeatherObservation)

    def say(msg):
        if stdout:
            stdout.write(msg)

    if reset:
        for m in (AuditLog, AuthorityAlert, CitizenReport, ForecastResult, CrossBorderEvent, SatelliteObservation,
                  SensorReading, WeatherObservation, HistoricalAQI, IndustrialZone, Hotspot, City, Country):
            m.objects.all().delete()
    elif Country.objects.exists():
        say("Demo data already present (use --reset to regenerate).")
        return

    rng = random.Random(42)
    now = timezone.now().replace(second=0, microsecond=0)

    # ---- users & roles -----------------------------------------------------
    User = get_user_model()
    for username, pwd, role, su in [("admin", "admin12345", "admin", True), ("authority", "authority123", "authority", False),
                                     ("citizen", "citizen123", "citizen", False)]:
        u, created = User.objects.get_or_create(username=username, defaults={"is_staff": su, "is_superuser": su})
        if created:
            u.set_password(pwd)
            u.save()
        Profile.objects.update_or_create(user=u, defaults={"role": role, "organisation": "Demo State Pollution Control Board" if role == "authority" else ""})

    # ---- geography ---------------------------------------------------------
    countries = {}
    for code, name, lat, lng, status, ver in COUNTRIES:
        countries[code] = Country.objects.create(code=code, name=name, lat=lat, lng=lng, shared_model_status=status, model_version=ver)
    cities = {}
    for cc, name, state, lat, lng, base, ind in CITIES:
        cities[name] = City.objects.create(country=countries[cc], name=name, state=state, lat=lat, lng=lng, base_aqi=base, is_industrial=ind)
    for cc, name, lat, lng, sector in INDUSTRIAL_ZONES:
        IndustrialZone.objects.create(country=countries[cc], name=name, lat=lat, lng=lng, sector=sector)

    # ---- hotspots (tuned so network mean AQI = 184, mean confidence = 92) --
    n = len(HOTSPOTS)
    aqis = []
    for code, city, *_ in HOTSPOTS:
        if code == KEY_CODE:
            aqis.append(312)
        else:
            aqis.append(int(cities[city].base_aqi * rng.uniform(1.0, 1.35)))
    diff = 184 * n - sum(aqis)
    others = [i for i, h in enumerate(HOTSPOTS) if h[0] != KEY_CODE]
    for k, i in enumerate(others):
        aqis[i] += diff // len(others) + (1 if k < diff % len(others) else 0)
    confs = [91 if h[0] == KEY_CODE else rng.randint(86, 97) for h in HOTSPOTS]
    cdiff = 92 * n - sum(confs)
    for k, i in enumerate(others):
        confs[i] += cdiff // len(others) + (1 if k < cdiff % len(others) else 0)
        confs[i] = max(70, min(98, confs[i]))

    compass = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    hs = {}
    ranked = sorted(range(n), key=lambda i: -aqis[i])
    predicted = set([0] + [i for i in ranked if i != 0][:13])  # 14 predicted events
    for i, (code, city, region, dlat, dlng, src, wdeg, downwind) in enumerate(HOTSPOTS):
        c = cities[city]
        aqi = aqis[i]
        pm25 = 187.0 if code == KEY_CODE else round(_pm_from_aqi(aqi) * rng.uniform(0.95, 1.05), 1)
        change = 2.8 if code == KEY_CODE else round(rng.uniform(1.1, 2.1), 1)
        sources = ALL_SOURCES if (code == KEY_CODE or rng.random() > 0.35) else rng.sample(ALL_SOURCES, 3)
        is_ind = "Industrial" in src or "Coal" in src
        h = Hotspot.objects.create(
            code=code, city=c, region=region, lat=round(c.lat + dlat, 4), lng=round(c.lng + dlng, 4),
            primary_pollutant="SO2" if "SO2" in src else "PM2.5", aqi=aqi, pm25=pm25,
            pm10=round(pm25 * rng.uniform(1.45, 1.8), 1), no2=round(rng.uniform(35, 95) * (1.3 if is_ind else 1), 1),
            so2=round(rng.uniform(12, 40) * (3.5 if "SO2" in src else 1.2 if is_ind else 1), 1),
            co=round(rng.uniform(0.8, 2.6), 2), status=aqi_status(aqi), confidence=confs[i], source_category=src,
            sources=sources, wind_deg=wdeg, wind_dir=compass[int((wdeg + 22.5) // 45) % 8],
            wind_speed=18.0 if code == KEY_CODE else round(rng.uniform(6, 22), 1), pm25_change=change,
            change_window_min=45 if code == KEY_CODE else rng.choice([60, 90, 120]),
            predicted_pm25=236.0 if code == KEY_CODE else round(pm25 * rng.uniform(1.05, 1.3), 1),
            predicted_event=i in predicted, detected_at=now - dt.timedelta(minutes=rng.randint(20, 600)),
        )
        if code == KEY_CODE:
            h.wind_dir = "SSW"
            h.detected_at = now - dt.timedelta(minutes=38)
            h.save()
        hs[code] = h
    key = hs[KEY_CODE]
    say(f"{n} hotspots created")

    # ---- sensor readings ---------------------------------------------------
    readings = []
    for h in hs.values():
        if h.code == KEY_CODE:
            for k in range(96, -1, -1):  # 15-min resolution, 24h
                t = now - dt.timedelta(minutes=15 * k)
                if k <= 3:  # the 2.8x spike within the last 45 minutes
                    pm = 66.8 + (187 - 66.8) * (3 - k) / 3
                else:
                    pm = 62 + 8 * math.sin(k / 9) + rng.uniform(-3, 3)
                readings.append(SensorReading(city=h.city, hotspot=h, timestamp=t, pm25=round(pm, 1), pm10=round(pm * 1.6, 1),
                                              no2=round(40 + pm * 0.25, 1), so2=round(18 + pm * 0.12, 1), co=round(0.9 + pm / 150, 2),
                                              aqi=int(pm * 1.65)))
        else:
            base = h.pm25 / h.pm25_change
            for k in range(24, -1, -1):
                t = now - dt.timedelta(hours=k)
                pm = h.pm25 if k == 0 else base * (1 + 0.12 * math.sin(k / 3)) * rng.uniform(0.92, 1.08)
                readings.append(SensorReading(city=h.city, hotspot=h, timestamp=t, pm25=round(pm, 1), pm10=round(pm * 1.6, 1),
                                              no2=round(h.no2 * rng.uniform(0.8, 1.1), 1), so2=round(h.so2 * rng.uniform(0.8, 1.1), 1),
                                              co=round(h.co * rng.uniform(0.85, 1.1), 2), aqi=int(h.aqi * pm / max(h.pm25, 1))))
    SensorReading.objects.bulk_create(readings)

    # ---- weather -----------------------------------------------------------
    weather = []
    for c in cities.values():
        t0 = 31 if c.lat < 35 and c.lat > 0 else (12 if c.lat > 45 else 24)
        for k in range(48, -1, -1):
            t = now - dt.timedelta(hours=k)
            diurnal = math.sin(((t.hour + 5.5 - 9) % 24) / 24 * 2 * math.pi)
            wdeg = 200 if c.name == "Ankleshwar" else (int(c.lng * 7) % 360)
            weather.append(WeatherObservation(city=c, timestamp=t, temperature=round(t0 + 5 * diurnal + rng.uniform(-1, 1), 1),
                                              humidity=round(55 - 15 * diurnal + rng.uniform(-4, 4), 1),
                                              wind_speed=18.0 if (c.name == "Ankleshwar" and k == 0) else round(rng.uniform(5, 20), 1),
                                              wind_deg=wdeg, rainfall=0.0 if rng.random() > 0.08 else round(rng.uniform(0.2, 4), 1)))
    WeatherObservation.objects.bulk_create(weather)

    # ---- 90-day history ----------------------------------------------------
    hist = []
    today = timezone.localdate()
    for c in cities.values():
        crop = c.name in ("Ludhiana", "Delhi", "Kanpur")
        for d in range(90, -1, -1):
            day = today - dt.timedelta(days=d)
            season = 1 + (0.35 if crop and d < 25 else 0) + 0.12 * math.sin(d / 6)
            aqi = int(c.base_aqi * season * rng.uniform(0.85, 1.15))
            fires = int(max(0, rng.gauss(18 if crop and d < 25 else 3, 3))) if c.country.code in ("IN", "BR") else int(max(0, rng.gauss(1.5, 1)))
            pm25 = round(_pm_from_aqi(aqi), 1)
            hist.append(HistoricalAQI(city=c, date=day, aqi=aqi, pm25=pm25, pm10=round(pm25 * 1.65, 1), fire_events=fires,
                                      temperature=round(28 + 4 * math.sin(d / 14) + rng.uniform(-2, 2), 1),
                                      humidity=round(55 + 15 * math.cos(d / 11) + rng.uniform(-5, 5), 1),
                                      wind_speed=round(rng.uniform(4, 20), 1)))
    HistoricalAQI.objects.bulk_create(hist)

    # ---- satellite observations -------------------------------------------
    sats = [SatelliteObservation(hotspot=key, country=countries["IN"], lat=key.lat + 0.004, lng=key.lng - 0.006,
                                 observed_at=now - dt.timedelta(minutes=52), obs_type="thermal_anomaly", intensity=0.82, confidence=88)]
    fire_regions = [("IN", 30.25, 75.85, 0.6, 26), ("IN", 30.95, 76.05, 0.4, 14), ("BR", -8.45, -63.5, 0.8, 22),
                    ("BR", -3.7, -59.8, 0.7, 12), ("RU", 50.5, 127.6, 0.4, 6), ("ZA", -25.8, 29.35, 0.2, 3)]
    for cc, la, ln, spread, count in fire_regions:
        for _ in range(count):
            sats.append(SatelliteObservation(country=countries[cc], lat=la + rng.uniform(-spread, spread), lng=ln + rng.uniform(-spread, spread),
                                             observed_at=now - dt.timedelta(hours=rng.uniform(0.5, 30)), obs_type="fire",
                                             intensity=rng.uniform(0.3, 1.0), confidence=rng.randint(60, 95)))
    for h in hs.values():
        if h.code != KEY_CODE and rng.random() > 0.3:
            sats.append(SatelliteObservation(hotspot=h, country=h.city.country, lat=h.lat + rng.uniform(-0.03, 0.03), lng=h.lng + rng.uniform(-0.03, 0.03),
                                             observed_at=now - dt.timedelta(hours=rng.uniform(1, 20)),
                                             obs_type=rng.choice(["aerosol", "no2_column", "thermal_anomaly"]),
                                             intensity=rng.uniform(0.4, 0.9), confidence=rng.randint(65, 92)))
    SatelliteObservation.objects.bulk_create(sats)

    # ---- citizen reports (1,284) -------------------------------------------
    reports = []
    idx = 1

    def mk(h, t, typ, lat, lng, status):
        nonlocal idx
        r = CitizenReport(code=f"CR-{idx:06d}", pollution_type=typ, description=rng.choice(VOICES), lat=round(lat, 5), lng=round(lng, 5),
                          location_label=h.region, city=h.city, hotspot=h, language=rng.choice(["en", "hi", "gu", "en", "mr"]),
                          ai_label=TYPE_LABEL[typ], ai_category=typ, ai_confidence=rng.randint(62, 92), ai_source="MOCK AI (DEMO)",
                          status=status, created_at=t)
        idx += 1
        return r

    for k in range(14):  # 14 reports around the key hotspot, 7 in the last hour
        t = now - dt.timedelta(minutes=rng.randint(5, 55)) if k < 7 else now - dt.timedelta(hours=rng.uniform(1.2, 5.5))
        reports.append(mk(key, t, "industrial" if k % 3 else "smoke", key.lat + rng.uniform(-0.02, 0.02), key.lng + rng.uniform(-0.02, 0.02), "AWAITING_VERIFICATION"))
    hs_list = [h for h in hs.values() if h.code != KEY_CODE]
    weights = [(3 if h.city.country.code == "IN" else 1) for h in hs_list]
    while idx <= 1284:
        h = rng.choices(hs_list, weights=weights)[0]
        cat = h.source_category.lower()
        typ = "crop_burning" if "agri" in cat else "industrial" if "industr" in cat or "coal" in cat else "garbage_burning" if "waste" in cat else "dust" if "dust" in cat else "smoke" if "fire" in cat else rng.choice(TYPES)
        if rng.random() < 0.2:
            typ = rng.choice(TYPES)
        age = rng.expovariate(1 / 240)  # hours
        t = now - dt.timedelta(hours=min(age, 24 * 60))
        status = rng.choices(["AWAITING_VERIFICATION", "CORROBORATED", "DISMISSED", "SUBMITTED"], weights=[45, 35, 8, 12])[0]
        reports.append(mk(h, t, typ, h.lat + rng.uniform(-0.08, 0.08), h.lng + rng.uniform(-0.08, 0.08), status))
    CitizenReport.objects.bulk_create(reports)
    for h in hs.values():
        h.citizen_report_count = CitizenReport.objects.filter(hotspot=h).count()
        h.save(update_fields=["citizen_report_count"])

    # ---- alerts --------------------------------------------------------------
    AuthorityAlert.objects.create(
        code="AL-0926-001", hotspot=key, severity="CRITICAL", title="CRITICAL POLLUTION EVENT",
        location="Gujarat Industrial Corridor", pollutant="PM2.5", current_value=187, predicted_value=236, confidence=92,
        evidence=["Sensor anomaly", "Citizen reports", "Satellite observation", "Wind trajectory"],
        created_at=now - dt.timedelta(minutes=31),
    )
    sev_for = {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MODERATE": "MEDIUM", "LOW": "LOW"}
    aidx = 2
    for h in sorted(hs_list, key=lambda x: -x.aqi)[:11]:
        sev = sev_for[h.status]
        AuthorityAlert.objects.create(
            code=f"AL-0926-{aidx:03d}", hotspot=h, severity=sev, title=f"{sev} POLLUTION EVENT", location=h.region,
            pollutant=h.primary_pollutant, current_value=h.pm25 if h.primary_pollutant == "PM2.5" else h.so2,
            predicted_value=h.predicted_pm25 if h.primary_pollutant == "PM2.5" else h.so2 * 1.2, confidence=h.confidence,
            evidence=rng.sample(["Sensor anomaly", "Citizen reports", "Satellite observation", "Wind trajectory", "Historical pattern"], 3),
            status=rng.choice(["NEW", "NEW", "ACKNOWLEDGED"]), created_at=now - dt.timedelta(minutes=rng.randint(40, 900)),
        )
        aidx += 1
    for sev, region, cc in [("LOW", "Cape Town — Atlantic seaboard", "Cape Town"), ("LOW", "Moscow — central", "Moscow"), ("MEDIUM", "Hyderabad — Jeedimetla", "Hyderabad")]:
        AuthorityAlert.objects.create(code=f"AL-0926-{aidx:03d}", severity=sev, title=f"{sev} POLLUTION EVENT", location=region,
                                      current_value=rng.uniform(25, 60), predicted_value=rng.uniform(30, 70), confidence=rng.randint(70, 85),
                                      evidence=["Sensor anomaly", "Historical pattern"], status="RESOLVED",
                                      created_at=now - dt.timedelta(hours=rng.randint(12, 40)))
        aidx += 1

    # ---- cross-border (FEDERATED ARCHITECTURE DEMONSTRATION) ---------------
    CrossBorderEvent.objects.create(code="XB-0926-001", origin_label="Demo Region A", affected_label="Demo Region B",
                                    origin_country=countries["RU"], affected_country=countries["CN"],
                                    origin_lat=50.49, origin_lng=127.63, affected_lat=49.2, affected_lng=129.9,
                                    corridor="Amur–Heilongjiang trade corridor", direction="SE", window="8–12 hours", confidence=84, risk="HIGH")
    CrossBorderEvent.objects.create(code="XB-0926-002", origin_label="Demo Region C", affected_label="Demo Region D",
                                    origin_country=countries["IN"], affected_country=countries["CN"],
                                    origin_lat=27.2, origin_lng=84.5, affected_lat=29.4, affected_lng=88.9,
                                    corridor="Indo-Gangetic Plain – Himalayan transport corridor", direction="NE", window="18–30 hours", confidence=71, risk="MODERATE")
    CrossBorderEvent.objects.create(code="XB-0926-003", origin_label="Demo Region E", affected_label="Demo Region F",
                                    origin_country=countries["BR"], affected_country=countries["ZA"],
                                    origin_lat=-8.6, origin_lng=-63.4, affected_lat=-26.0, affected_lng=28.5,
                                    corridor="South Atlantic long-range smoke corridor", direction="E", window="5–7 days", confidence=62, risk="MODERATE")

    # ---- forecast results --------------------------------------------------
    for hz, aqi, prob in [(6, 168, 72), (12, 193, 84), (24, 221, 91), (48, 196, 78)]:
        ForecastResult.objects.create(hotspot=key, city=key.city, horizon_hours=hz, aqi=aqi, pm25=round(_pm_from_aqi(aqi), 1),
                                      spike_probability=prob, risk=aqi_status(aqi), confidence=86, model_source="SIMULATED")
    say(f"Seed complete: {CitizenReport.objects.count()} reports, {AuthorityAlert.objects.count()} alerts, "
        f"{SensorReading.objects.count()} sensor readings, {HistoricalAQI.objects.count()} history rows.")
