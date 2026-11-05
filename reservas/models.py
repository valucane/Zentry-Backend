from django.db import models
from . import ReservaState, ReservaHistoricoState

class LugarComun(models.Model):
    codigo = models.SlugField(max_length=50, unique=True, default='cancha-tenis')
    nombre = models.CharField(max_length=100)
    horas_turno = models.SmallIntegerField(default=1)
    duracion_minutos = models.IntegerField(null=True, blank=True, default=60)
    max_personas = models.IntegerField(default=4)
    hora_apertura = models.SmallIntegerField(default=9)
    hora_cierre = models.SmallIntegerField(default=24)
    es_dia_completo = models.BooleanField(default=False)
    es_capacidad_variable = models.BooleanField(default=False)
    tipo_accion = models.CharField(max_length=20, default='confirmar')
    lote = models.OneToOneField(
        'administracion.Lote',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='lugarescomun_lote'
    )

    def __str__(self):
        return self.nombre

class Reserva(models.Model):
    socio = models.ForeignKey('administracion.Socio', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservas')
    lugar = models.ForeignKey(LugarComun, on_delete=models.CASCADE, related_name='reservas_lote')
    fecha_desde = models.DateTimeField()
    fecha_hasta = models.DateTimeField()
    horario_texto = models.CharField(max_length=50, blank=True, default='')
    estado = models.CharField(max_length=20, choices=ReservaState.CHOICES, default=ReservaState.aprobado)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lugar.nombre} - {self.fecha_desde.strftime('%Y-%m-%d')}"

class ReservaHistorico(models.Model):
    socio = models.ForeignKey('administracion.Socio', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservas_trace')
    lugar = models.ForeignKey(LugarComun, on_delete=models.CASCADE, related_name='reservas_trace_lote')
    fecha_desde = models.DateTimeField()
    fecha_hasta = models.DateTimeField()
    detalles = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ReservaHistoricoState.CHOICES, default=ReservaHistoricoState.ok)
