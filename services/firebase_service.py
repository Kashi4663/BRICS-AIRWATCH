"""Firebase architecture placeholder: auth, real-time reports, notifications.

Server-side calls use firebase-admin with GOOGLE_APPLICATION_CREDENTIALS
when FIREBASE_PROJECT_ID is set. No credentials are ever sent to the browser.
"""
import logging

from .config import cfg, is_configured

log = logging.getLogger("airwatch")


def is_live() -> bool:
    if not is_configured("FIREBASE_PROJECT_ID"):
        return False
    try:
        import firebase_admin  # noqa: F401
        return True
    except Exception:
        return False


def _app():
    import firebase_admin

    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": cfg("FIREBASE_PROJECT_ID")})
    return firebase_admin.get_app()


def publish_report(report: dict):
    """Push a new citizen report to Firestore collection `live_reports`."""
    if not is_live():
        return {"mode": "LOCAL"}
    try:
        from firebase_admin import firestore

        firestore.client(_app()).collection("live_reports").document(report["code"]).set(report)
        return {"mode": "FIREBASE"}
    except Exception as exc:
        log.warning("Firebase publish failed: %s", exc)
        return {"mode": "ERROR"}


def notify_authorities(alert: dict):
    """Send an FCM topic notification for a new alert (topic: authority-alerts)."""
    if not is_live():
        return {"mode": "LOCAL"}
    try:
        from firebase_admin import messaging

        msg = messaging.Message(
            topic="authority-alerts",
            notification=messaging.Notification(title=f"[{alert['severity']}] {alert['title']}", body=alert["location"]),
        )
        messaging.send(msg, app=_app())
        return {"mode": "FIREBASE"}
    except Exception as exc:
        log.warning("FCM send failed: %s", exc)
        return {"mode": "ERROR"}
