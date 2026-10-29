from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Invitacion, InvitacionHistorico, RegistroAcceso
from .qr import crear_token_qr, obtener_dia_semana, obtener_id_invitacion
from .serializers import InvitacionFrontendSerializer


class InvitacionViewSet(viewsets.ModelViewSet):
    queryset = Invitacion.objects.select_related('invitado', 'punto_acceso', 'socio').all().order_by('-fecha_creacion')
    serializer_class = InvitacionFrontendSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        solo_activas = self.request.query_params.get('activas')
        if solo_activas == 'true':
            qs = qs.filter(Q(tipo='recurrente') | Q(usada_en__isnull=True))
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        data = serializer.data
        data['qrToken'] = crear_token_qr(serializer.instance.pk)
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['POST', 'PUT'])
    def usar(self, request, pk=None):
        """Valida el token QR y registra un ingreso para esta invitacion."""
        invitacion = self.get_object()
        token = request.data.get('token') if hasattr(request.data, 'get') else None
        if not isinstance(token, str) or not token:
            return Response(
                {'detail': 'Debe enviar el token del QR.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if obtener_id_invitacion(token) != invitacion.pk:
            return Response(
                {'detail': 'El token no corresponde a esta invitacion.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._registrar_ingreso(invitacion.pk)

    @action(detail=False, methods=['POST'], url_path='validar-qr')
    def validar_qr(self, request):
        token = request.data.get('token') if hasattr(request.data, 'get') else None
        if not isinstance(token, str) or not token:
            return Response(
                {'detail': 'Debe enviar el token del QR.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitacion_id = obtener_id_invitacion(token)
        if invitacion_id is None:
            return Response(
                {'detail': 'El token del QR no es valido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._registrar_ingreso(invitacion_id)

    def _registrar_ingreso(self, invitacion_id):
        with transaction.atomic():
            try:
                invitacion = Invitacion.objects.select_related('invitado', 'punto_acceso', 'socio').get(pk=invitacion_id)
            except Invitacion.DoesNotExist:
                return Response(
                    {'detail': 'La invitacion no existe.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            ahora = timezone.now()
            hoy = timezone.localdate(ahora)
            fecha_inicio = timezone.localtime(invitacion.fecha_inicio).date()
            fecha_fin = timezone.localtime(invitacion.fecha_visita).date()
            if not fecha_inicio <= hoy <= fecha_fin:
                return Response(
                    {'detail': 'La invitacion no esta vigente para hoy.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if invitacion.tipo == 'recurrente':
                dias_permitidos = {
                    obtener_dia_semana(dia)
                    for dia in (invitacion.dias_semana or [])
                    if isinstance(dia, str)
                }
                if hoy.weekday() not in dias_permitidos:
                    return Response(
                        {'detail': 'La invitacion no esta habilitada para hoy.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                if (
                    invitacion.usada_en
                    and timezone.localdate(invitacion.usada_en) == hoy
                ):
                    return Response(
                        {'detail': 'La invitacion recurrente ya fue usada hoy.'},
                        status=status.HTTP_409_CONFLICT,
                    )
            elif invitacion.tipo == 'unica':
                if invitacion.usada_en:
                    return Response(
                        {'detail': 'La invitacion ya fue usada.'},
                        status=status.HTTP_409_CONFLICT,
                    )
            else:
                return Response(
                    {'detail': 'El tipo de invitacion no es valido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            invitacion.usada_en = ahora
            invitacion.save(update_fields=['usada_en'])
            InvitacionHistorico.objects.create(
                invitado=invitacion.invitado,
                socio=invitacion.socio,
                punto_acceso=invitacion.punto_acceso,
                fecha_creacion=invitacion.fecha_creacion,
                fecha_inicio=invitacion.fecha_inicio,
                fecha_visita=invitacion.fecha_visita,
                fecha_fin=ahora,
                dias_habilitados=invitacion.dias_habilitados,
                estado='recepcionado',
                tipo=invitacion.tipo,
            )

        return Response(self.get_serializer(invitacion).data)

    @action(detail=False, methods=['POST'], url_path='registrar-egreso')
    def registrar_egreso(self, request):
        """Registra el egreso de una lista de DNIs desde la pantalla del Guardia."""
        dnis = request.data.get('dnis', [])
        if not isinstance(dnis, list) or not dnis:
            return Response({'detail': 'Debe enviar una lista de DNIs.'}, status=status.HTTP_400_BAD_REQUEST)

        ahora = timezone.now()
        registros = [
            RegistroAcceso(
                dni=str(dni).strip(),
                tipo_movimiento='egreso',
                hora_desde=ahora.time(),
                hora_hasta=ahora.time(),
                valido_desde=ahora,
                valido_hasta=ahora,
            )
            for dni in dnis
        ]
        RegistroAcceso.objects.bulk_create(registros)

        return Response({
            'status': 'ok',
            'cantidad': len(registros),
            'mensaje': f'Se registraron {len(registros)} egresos correctamente en la base de datos.'
        }, status=status.HTTP_201_CREATED)
