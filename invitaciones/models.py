from django.db import models
from django.utils import timezone

from base.models import ActiveStatusModel, Persona
from . import InvitacionTipo, InvitacionEstado

# --- Invitaciones --- #

class Invitado(Persona):

    def can_delete(self):
        return not self.invitaciones_vigentes.exists()

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.dni})".strip()


class Invitacion(models.Model):
    invitado = models.ForeignKey(Invitado, on_delete=models.PROTECT, related_name='invitaciones_vigentes')
    socio = models.ForeignKey('administracion.Socio', on_delete=models.PROTECT, null=True, blank=True, related_name='invitaciones_vigentes')
    punto_acceso = models.ForeignKey('administracion.PuntoAcceso', on_delete=models.CASCADE, null=True, blank=True, related_name='invitaciones_vigentes')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_visita = models.DateTimeField(default=timezone.now)
    dias_habilitados = models.PositiveIntegerField(default=0)
    dias_semana = models.JSONField(default=list, blank=True)
    tipo = models.CharField(max_length=20, choices=InvitacionTipo.CHOICES, default=InvitacionTipo.unica)
    usada_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invitación {self.tipo} - {self.invitado}"

# --- Proveedores --- #

class AutorizacionProveedor(models.Model):
    socio = models.ForeignKey('administracion.Socio', on_delete=models.PROTECT, related_name='autorizaciones_proveedor')
    proveedor = models.OneToOneField('administracion.Proveedor', on_delete=models.CASCADE, related_name='autorizaciones')
    hora_desde = models.TimeField()
    hora_hasta = models.TimeField()
    valido_desde = models.DateField()
    valido_hasta = models.DateField(null=True, blank=True)

# --- Trace --- #

class InvitacionHistorico(models.Model):
    invitado = models.ForeignKey(Invitado, on_delete=models.CASCADE, related_name='invitaciones')
    socio = models.ForeignKey('administracion.Socio', on_delete=models.CASCADE, null=True, blank=True, related_name='invitaciones')
    punto_acceso = models.ForeignKey('administracion.PuntoAcceso', on_delete=models.CASCADE, null=True, blank=True, related_name='invitaciones')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_visita = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(default=timezone.now)
    dias_habilitados = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=InvitacionEstado.CHOICES, default=InvitacionEstado.recepcionado)
    tipo = models.CharField(max_length=20, choices=InvitacionTipo.CHOICES, default=InvitacionTipo.unica)

class RegistroAcceso(ActiveStatusModel):
    dni = models.CharField(max_length=20, blank=True, default='')
    tipo_movimiento = models.CharField(max_length=20, default='egreso')  # 'ingreso' | 'egreso'
    hora_desde = models.TimeField(default=timezone.now)
    hora_hasta = models.TimeField(default=timezone.now)
    valido_desde = models.DateTimeField(default=timezone.now)
    valido_hasta = models.DateTimeField(default=timezone.now)
