"""All REST endpoints in one place."""
from django.urls import path

from ai_engine import api as ai_api
from alerts import api as alerts_api
from citizen_reports import api as reports_api
from data_engine import api as data_api
from forecasting import api as forecast_api
from geospatial import api as geo_api
from pollution import api as pollution_api

urlpatterns = [
    path("dashboard/", pollution_api.dashboard, name="api-dashboard"),
    path("status/", pollution_api.system_status, name="api-status"),
    path("hotspots/", pollution_api.hotspot_list, name="api-hotspots"),
    path("hotspots/<str:code>/", pollution_api.hotspot_detail, name="api-hotspot-detail"),
    path("map/layers/", geo_api.map_layers, name="api-map-layers"),
    path("reports/", reports_api.ReportView.as_view(), name="api-reports"),
    path("voice/process/", reports_api.VoiceProcessView.as_view(), name="api-voice"),
    path("ai/analyze-image/", ai_api.AnalyzeImageView.as_view(), name="api-analyze-image"),
    path("ai/investigate/", ai_api.InvestigateView.as_view(), name="api-investigate"),
    path("forecast/", forecast_api.forecast, name="api-forecast"),
    path("cross-border/", geo_api.cross_border, name="api-cross-border"),
    path("alerts/", alerts_api.alert_list, name="api-alerts"),
    path("alerts/<str:code>/acknowledge/", alerts_api.AlertActionView.as_view(action_name="acknowledge"), name="api-alert-ack"),
    path("alerts/<str:code>/resolve/", alerts_api.AlertActionView.as_view(action_name="resolve"), name="api-alert-resolve"),
    path("data/", data_api.data_explorer, name="api-data"),
    path("assistant/", ai_api.AssistantView.as_view(), name="api-assistant"),
]
