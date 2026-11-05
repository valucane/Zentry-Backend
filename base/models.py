from django.db import models

class ActiveManager(models.Manager):
    """ The boolean field 'is_active' is required for this to work """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ActiveStatusModel(models.Model):
    is_active = models.BooleanField(default=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class Persona(ActiveStatusModel):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, default='')
    dni = models.CharField(max_length=20)

    def apellido_nombre(self):
        return f"{self.apellido} {self.nombre}".strip()

    def a_nombre(self):
        return f"{self.apellido[:1]} {self.nombre}".strip()

    class Meta:
        abstract = True
