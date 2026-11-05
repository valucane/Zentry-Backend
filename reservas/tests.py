from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from administracion.models import Lote, Socio
from invitaciones.models import Invitado, InvitacionHistorico, RegistroAcceso


class UltimosMovimientosTests(TestCase):
    def test_historial_incluye_egresos_registrados(self):
        ahora = timezone.now()
        lote = Lote.objects.create(numero=101)
        socio = Socio.objects.create(
            nombre='Residente',
            apellido='Prueba',
            dni='40101010',
            lote=lote,
        )
        RegistroAcceso.objects.create(
            dni=socio.dni,
            tipo_movimiento='egreso',
            valido_desde=ahora,
            valido_hasta=ahora,
        )

        client = APIClient()
        client.force_authenticate(user=User.objects.create_user(username='guardia-test'))
        response = client.get(reverse('ultimos-movimientos'))

        self.assertEqual(response.status_code, 200)
        egresos = [item for item in response.data if item['tipo'] == 'egreso']
        self.assertEqual(len(egresos), 1)
        self.assertEqual(egresos[0]['detalle'], 'DNI: 40101010')
        self.assertEqual(egresos[0]['descripcion'], 'Egreso registrado')
        self.assertEqual(egresos[0]['nombre'], 'Residente Prueba')

    def test_historial_requiere_autenticacion(self):
        response = APIClient().get(reverse('ultimos-movimientos'))

        self.assertEqual(response.status_code, 401)

    def test_historial_incluye_nombre_del_invitado(self):
        invitado = Invitado.objects.create(
            nombre='Visitante',
            apellido='Prueba',
            dni='40101011',
        )
        InvitacionHistorico.objects.create(
            invitado=invitado,
            fecha_fin=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=User.objects.create_user(username='guardia-test'))
        response = client.get(reverse('ultimos-movimientos'))

        self.assertEqual(response.status_code, 200)
        ingresos = [item for item in response.data if item['tipo'] == 'visitante-aprobado']
        self.assertEqual(len(ingresos), 1)
        self.assertEqual(ingresos[0]['nombre'], 'Visitante Prueba')

# Create your tests here.
