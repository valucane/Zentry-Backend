from django.contrib import admin
from django.urls import path, include
from reservas.views import InstalacionBarrioViewSet, ultimos_movimientos_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('administracion.urls')),
    path('api/invitaciones/', include('invitaciones.urls')),
    path('api/reservas/', include('reservas.urls')),
    path('api/eventos/', include('eventos.urls')),
    path('api/barrios/instalaciones/', InstalacionBarrioViewSet.as_view({'get': 'list'}), name='barrios-instalaciones'),
    path('api/movimientos/', ultimos_movimientos_view, name='ultimos-movimientos'),
]
