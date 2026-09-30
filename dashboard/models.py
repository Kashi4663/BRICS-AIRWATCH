from django.conf import settings
from django.db import models

ROLES = [("citizen", "Citizen"), ("authority", "Authority"), ("admin", "Administrator")]


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=12, choices=ROLES, default="citizen")
    organisation = models.CharField(max_length=128, blank=True)
    preferred_language = models.CharField(max_length=8, default="en")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


def user_role(user):
    if not user or not user.is_authenticated:
        return "guest"
    if user.is_superuser:
        return "admin"
    profile = getattr(user, "profile", None)
    return profile.role if profile else "citizen"
