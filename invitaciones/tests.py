from datetime import timedelta
from django.db import connection
from django.test.utils import CaptureQueriesContext

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from administracion.models import Lote, PuntoAcceso, Socio
from .models import Invitacion, Invitado, InvitacionHistorico, RegistroAcceso
from .qr import crear_token_qr, obtener_id_invitacion


class InvitacionQRTests(TestCase):
    def setUp(self):
        lote = Lote.objects.create(numero=101)
        self.socio = Socio.objects.create(
            nombre='Residente',
            apellido='Prueba',
            dni='30101010',
            lote=lote,
        )
        self.invitado = Invitado.objects.create(
            nombre='Visitante',
            apellido='Prueba',
            dni='40101010',
        )
        self.punto_acceso = PuntoAcceso.objects.create(nombre='Porton de prueba')
        ahora = timezone.now()
        self.invitacion = Invitacion.objects.create(
            invitado=self.invitado,
            socio=self.socio,
            punto_acceso=self.punto_acceso,
            fecha_inicio=ahora,
            fecha_visita=ahora,
            tipo='unica',
        )
        self.client = APIClient()
        self.url = reverse('invitaciones-validar-qr')

    def escanear(self, invitacion=None):
        invitacion = invitacion or self.invitacion
        return self.client.post(
            self.url,
            {'token': crear_token_qr(invitacion.pk)},
            format='json',
        )

    def test_crear_invitacion_devuelve_token_qr(self):
        hoy = timezone.localdate().isoformat()
        response = self.client.post(
            reverse('invitaciones-list'),
            {
                'nombreVisitante': 'Otro Visitante',
                'dni': '40101011',
                'porton': 'Porton de prueba',
                'tipo': 'unica',
                'fechaInicio': hoy,
                'fechaFin': hoy,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['qrToken'])
        self.assertEqual(
            obtener_id_invitacion(response.data['qrToken']),
            int(response.data['id']),
        )

    def test_listar_invitaciones_activas_devuelve_token_qr(self):
        response = self.client.get(
            reverse('invitaciones-list'),
            {'activas': 'true'},
        )

        self.assertEqual(response.status_code, 200)
        invitacion = next(
            item for item in response.data
            if item['id'] == str(self.invitacion.id)
        )
        self.assertTrue(invitacion['qrToken'])
        self.assertEqual(
            obtener_id_invitacion(invitacion['qrToken']),
            self.invitacion.id,
        )

    def test_qr_de_invitacion_unica_solo_se_acepta_una_vez(self):
        primera_lectura = self.escanear()
        segunda_lectura = self.escanear()

        self.assertEqual(primera_lectura.status_code, 200)
        self.assertEqual(segunda_lectura.status_code, 409)
        self.assertEqual(InvitacionHistorico.objects.count(), 1)

    def test_qr_recurrente_solo_se_acepta_una_vez_por_dia_habilitado(self):
        hoy = timezone.localdate()
        dias_semana = [
            'lunes',
            'martes',
            'miercoles',
            'jueves',
            'viernes',
            'sabado',
            'domingo',
        ]
        self.invitacion.tipo = 'recurrente'
        self.invitacion.dias_semana = [dias_semana[hoy.weekday()]]
        self.invitacion.save(update_fields=['tipo', 'dias_semana'])

        primera_lectura = self.escanear()
        segunda_lectura = self.escanear()

        self.assertEqual(primera_lectura.status_code, 200)
        self.assertEqual(segunda_lectura.status_code, 409)
        self.assertEqual(InvitacionHistorico.objects.count(), 1)

    def test_qr_recurrente_vuelve_a_aceptarse_en_otro_dia_habilitado(self):
        hoy = timezone.localdate()
        dias_semana = [
            'lunes',
            'martes',
            'miercoles',
            'jueves',
            'viernes',
            'sabado',
            'domingo',
        ]
        self.invitacion.tipo = 'recurrente'
        self.invitacion.dias_semana = [dias_semana[hoy.weekday()]]
        self.invitacion.usada_en = timezone.now() - timedelta(days=1)
        self.invitacion.save(update_fields=['tipo', 'dias_semana', 'usada_en'])

        response = self.escanear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(InvitacionHistorico.objects.count(), 1)

    def test_qr_recurrente_rechaza_dia_no_habilitado(self):
        self.invitacion.tipo = 'recurrente'
        self.invitacion.dias_semana = ['dia-invalido']
        self.invitacion.save(update_fields=['tipo', 'dias_semana'])

        response = self.escanear()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(InvitacionHistorico.objects.count(), 0)

    def test_qr_rechaza_token_invalido(self):
        response = self.client.post(
            self.url,
            {'token': 'token-invalido'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_registrar_egreso_inserta_varios_dnis_en_una_consulta(self):
        dnis = [f'401010{numero:02d}' for numero in range(25)]

        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(
                reverse('invitaciones-registrar-egreso'),
                {'dnis': dnis},
                format='json',
            )

        inserts = [
            query for query in queries
            if query['sql'].lstrip().upper().startswith('INSERT')
        ]
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['cantidad'], len(dnis))
        self.assertEqual(RegistroAcceso.objects.count(), len(dnis))
        self.assertEqual(len(inserts), 1)
        self.assertEqual(
            list(RegistroAcceso.objects.values_list('dni', flat=True)),
            dnis,
        )
