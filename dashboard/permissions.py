from rest_framework.permissions import BasePermission

from .models import user_role


class IsAuthority(BasePermission):
    message = "Authority or admin role required. Sign in as an authority user."

    def has_permission(self, request, view):
        return user_role(request.user) in ("authority", "admin")
