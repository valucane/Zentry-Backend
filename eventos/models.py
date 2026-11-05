from django.db import models

from . import AlertaState

class BotonPanico(models.Model):
    estado = models.CharField(choices=AlertaState.CHOICES, default=AlertaState.pendiente)
    razon = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('administracion.Socio', on_delete=models.SET_NULL, null=True, related_name='alertas_creadas')
    lote = models.ForeignKey('administracion.Lote', on_delete=models.SET_NULL, null=True, related_name='alertas')
    motivo_rechazo = models.CharField(max_length=30, null=True, blank=True)