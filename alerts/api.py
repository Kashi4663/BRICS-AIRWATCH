import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from alerts.models import AuditLog, AuthorityAlert
from dashboard.permissions import IsAuthority

audit = logging.getLogger("airwatch.audit")


@api_view(["GET"])
def alert_list(request):
    qs = AuthorityAlert.objects.select_related("hotspot", "acknowledged_by", "resolved_by")
    sev = request.GET.get("severity")
    status = request.GET.get("status")
    if sev:
        qs = qs.filter(severity=sev.upper()[:10])
    if status:
        qs = qs.filter(status=status.upper()[:14])
    counts = {s: AuthorityAlert.objects.filter(severity=s).exclude(status="RESOLVED").count() for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    items = sorted(qs, key=lambda a: (a.status == "RESOLVED", order[a.severity], -a.created_at.timestamp()))
    return Response({"data_label": "DEMO DATA", "counts": counts, "results": [a.to_dict() for a in items],
                     "notice": "Alerts are AI-generated decision support on demo data. They are not government enforcement actions."})


class AlertActionView(APIView):
    permission_classes = [IsAuthority]
    action_name = "acknowledge"

    def post(self, request, code):
        alert = get_object_or_404(AuthorityAlert, code=code[:32])
        now = timezone.now()
        if self.action_name == "acknowledge":
            alert.status, alert.acknowledged_by, alert.acknowledged_at = "ACKNOWLEDGED", request.user, now
        else:
            alert.status, alert.resolved_by, alert.resolved_at = "RESOLVED", request.user, now
        alert.save()
        ip = request.META.get("REMOTE_ADDR")
        AuditLog.objects.create(user=request.user, action=f"alert.{self.action_name}", target=alert.code,
                                detail={"severity": alert.severity, "location": alert.location}, ip=ip)
        audit.info("user=%s action=alert.%s target=%s ip=%s", request.user.username, self.action_name, alert.code, ip)
        return Response(alert.to_dict())
