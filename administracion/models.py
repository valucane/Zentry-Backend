from django.db import models
from django.contrib.auth.models import User

from base import AccountRole
from base.models import Persona, ActiveStatusModel
from . import LoteEstado, PuntoAccesoTipo, PuntoAccesoEstado

class Account(ActiveStatusModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account')
    role = models.CharField(max_length=20, choices=AccountRole.ROLES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

# --- Barrio --- #

class Lote(models.Model):
    numero = models.IntegerField(unique=True)
    estado = models.CharField(max_length=20, choices=LoteEstado.CHOICES, default=LoteEstado.libre)

    def __str__(self):
        return f"Lote {self.numero}"

class PuntoAcceso(models.Model):
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=PuntoAccesoTipo.CHOICES, default=PuntoAccesoTipo.mixto)
    estado = models.CharField(max_length=20, choices=PuntoAccesoEstado.CHOICES, default=PuntoAccesoEstado.abierto)

    def __str__(self):
        return self.nombre

# --- Actores --- #

class Administrador(Persona):
    account = models.OneToOneField(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='administrador_perfil')
    email = models.EmailField(blank=True, default='')

    def __str__(self):
        return self.apellido_nombre()

class Guardia(Persona):
    account = models.OneToOneField(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='guardia_perfil')
    email = models.EmailField(blank=True, default='')

    def __str__(self):
        return self.apellido_nombre()

class Socio(Persona):
    TIPO_CHOICES = [
        ('propietario', 'Propietario'),
        ('inquilino', 'Inquilino'),
    ]
    ROL_PROPIEDAD_CHOICES = [
        ('titular', 'Titular'),
        ('conviviente', 'Conviviente'),
    ]

    account = models.OneToOneField(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='socio_perfil')
    email = models.EmailField(blank=True, default='')
    telefono = models.CharField(max_length=30, blank=True, default='')
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='socios')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='propietario')
    rol_propiedad = models.CharField(max_length=20, choices=ROL_PROPIEDAD_CHOICES, default='titular')
    patentes = models.JSONField(default=list, blank=True)
    fecha_inicio_contrato = models.DateField(null=True, blank=True)
    fecha_fin_contrato = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido} (Lote {self.lote.numero if self.lote else '-'})"

class Proveedor(Persona):
    telefono = models.CharField(max_length=30)

    def __str__(self):
        return self.apellido_nombre()
