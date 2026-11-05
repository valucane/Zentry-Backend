from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    BasePermission,
)
from . import AccountRole

class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser

def _cuenta_activa_con_rol(user, rol):
    if not user.is_authenticated:
        return False
    account = getattr(user, 'account', None)
    if account is None:
        return False
    return account.is_active and account.role == rol


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return _cuenta_activa_con_rol(request.user, AccountRole.admin)


class IsGuardiaRole(BasePermission):
    def has_permission(self, request, view):
        return _cuenta_activa_con_rol(request.user, AccountRole.guardia)


class IsSocioRole(BasePermission):
    def has_permission(self, request, view):
        return _cuenta_activa_con_rol(request.user, AccountRole.socio)