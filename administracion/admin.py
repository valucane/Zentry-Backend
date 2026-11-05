from django.contrib import admin
from . import models

admin.site.register(models.Administrador)
admin.site.register(models.Guardia)
admin.site.register(models.Socio)
admin.site.register(models.Account)
admin.site.register(models.Proveedor)
admin.site.register(models.Lote)
admin.site.register(models.PuntoAcceso)