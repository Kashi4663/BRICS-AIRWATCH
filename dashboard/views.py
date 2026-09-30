from django.contrib.auth.views import LoginView
from django.http import Http404
from django.shortcuts import render

from services import speech_service
from services.bigquery_service import schema_json
from services.config import service_status
from services.demo_data import KEY_CODE

PAGES = {
    "overview": "Global Intelligence Dashboard",
    "map": "Live Pollution Map",
    "hotspots": "Pollution Hotspots",
    "investigate": "AI Investigation Center",
    "forecast": "Pollution Forecast",
    "cross-border": "Cross-Border Intelligence",
    "reports": "Citizen Reports",
    "report": "Report Pollution",
    "alerts": "Authority Alerts",
    "data": "Data Explorer",
    "analytics": "Climate Analytics",
    "assistant": "AIRWATCH AI",
    "settings": "Settings",
}


def landing(request):
    return render(request, "landing.html")


def page(request, slug):
    if slug not in PAGES:
        raise Http404
    ctx = {"page": slug, "page_title": PAGES[slug], "key_hotspot": request.GET.get("hotspot", KEY_CODE)[:32],
           "languages": speech_service.LANGUAGES}
    if slug == "settings":
        ctx["services"] = service_status()
        ctx["schemas"] = schema_json()
    return render(request, f"pages/{slug.replace('-', '_')}.html", ctx)


class AirwatchLoginView(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True
