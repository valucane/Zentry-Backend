from django.urls import path

from . import views

urlpatterns = [
    path('stream/', views.stream),
    path('panico/', views.alerta_panico_view, name='eventos-panico'),
    path('pendientes/', views.alertas_pendientes, name='eventos-pendientes'),
    path('panico/<int:pk>/', views.AlertaRecepcionarView.as_view(), name='eventos-panico-recepcionar'),
    path('historico/', views.historico_alertas, name='eventos-historico'),
]
