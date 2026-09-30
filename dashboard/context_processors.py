from django.utils import timezone

from services.config import demo_mode

from .models import user_role

NAV = [
    ("overview", "Overview", "grid"), ("map", "Live Map", "map"), ("hotspots", "Hotspots", "target"),
    ("forecast", "Forecast", "trend"), ("investigate", "AI Investigate", "cpu"), ("cross-border", "Cross-Border", "globe"),
    ("reports", "Citizen Reports", "users"), ("alerts", "Alerts", "bell"), ("data", "Data Explorer", "db"),
    ("analytics", "Climate Analytics", "bars"), ("assistant", "AI Assistant", "spark"),
]
MOBILE_NAV = [("overview", "Overview", "grid"), ("map", "Map", "map"), ("report", "Report", "plus"),
              ("alerts", "Alerts", "bell"), ("assistant", "AI", "spark")]


def platform(request):
    return {
        "NAV": NAV,
        "MOBILE_NAV": MOBILE_NAV,
        "DEMO_MODE": demo_mode(),
        "USER_ROLE": user_role(getattr(request, "user", None)),
        "NOW": timezone.localtime(),
    }
