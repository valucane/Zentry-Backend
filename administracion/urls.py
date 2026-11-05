from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdministradorViewSet,
    GuardiaViewSet,
    LoteViewSet,
    PuntoAccesoViewSet,
    SocioViewSet,
    login_view,
    recuperar_contrasena_view,
)

router = DefaultRouter()
router.register(r'administradores', AdministradorViewSet, basename='administradores')
router.register(r'residentes', SocioViewSet, basename='residentes')
router.register(r'guardias', GuardiaViewSet, basename='guardias')
router.register(r'guardia', GuardiaViewSet, basename='guardia')
router.register(r'lotes', LoteViewSet, basename='lotes')
router.register(r'puntos-acceso', PuntoAccesoViewSet, basename='puntos-acceso')

urlpatterns = [
    path('auth/login/', login_view, name='api-login'),
    path('auth/recuperar-contrasena/', recuperar_contrasena_view, name='api-recuperar-contrasena'),
    path('guardia', GuardiaViewSet.as_view({'post': 'create'}), name='guardia-create-no-slash'),
    path('', include(router.urls)),
]
