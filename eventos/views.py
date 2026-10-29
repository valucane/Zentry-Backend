from django.db import transaction
from django.http import StreamingHttpResponse
from rest_framework import status, views
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from administracion.models import Socio
from base.permissions import IsGuardiaRole, IsAdminRole, IsSocioRole
from .models import BotonPanico, AlertaState
from .serializers import AlertaSerializer
from .services import eventos


@api_view(['POST'])
@permission_classes([IsSocioRole])
def alerta_panico_view(request):
    """El socio autenticado genera una alerta sobre su propio lote."""
    socio = Socio.objects.select_related('lote').filter(
        account=request.user.account, is_active=True
    ).first()
    if not socio or not socio.lote_id:
        return Response({'detail': 'El socio debe tener un lote asignado.'}, status=status.HTTP_400_BAD_REQUEST)
    if not socio.telefono.strip():
        return Response({'detail': 'El socio debe tener un teléfono registrado.'}, status=status.HTTP_400_BAD_REQUEST)
    razon = str(request.data.get('razon') or 'Emergencia').strip()[:30] or 'Emergencia'
    alerta = BotonPanico.objects.create(created_by=socio, lote=socio.lote, razon=razon)
    return Response({
        'mensaje': 'Alerta registrada y disponible para seguridad.',
        'alerta': AlertaSerializer(alerta).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsGuardiaRole])
def stream(request):
    """Conserva el endpoint SSE que ya expone la rama eventos."""
    response = StreamingHttpResponse(eventos(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['GET'])
@permission_classes([IsGuardiaRole])
def alertas_pendientes(request):
    alertas = BotonPanico.objects.filter(
        estado__in=[AlertaState.pendiente, AlertaState.enviada]
    ).select_related('created_by', 'lote').order_by('created_at', 'pk')
    response = Response(AlertaSerializer(alertas, many=True).data)
    response['Cache-Control'] = 'no-store'
    return response


class AlertaRecepcionarView(views.APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsGuardiaRole]

    def put(self, request, pk):
        accion = request.data.get('accion')
        if accion is None and 'rechazada' in request.data:
            # Compatibilidad con el contrato previo de la rama eventos.
            rechazada = request.data.get('rechazada')
            accion = 'rechazar' if rechazada in (True, 'true', 'True', 1, '1') else 'enviar_movil'
        if accion not in ('enviar_movil', 'rechazar'):
            return Response({'detail': 'Acción inválida.'}, status=status.HTTP_400_BAD_REQUEST)
        motivo = str(request.data.get('motivo_rechazo') or '').strip()
        if accion == 'rechazar' and not motivo:
            return Response({'detail': 'Indicá el motivo del rechazo.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(motivo) > 30:
            return Response({'detail': 'El motivo no puede superar 30 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            alerta = BotonPanico.objects.select_related('created_by', 'lote').get(pk=pk)
            if not alerta:
                return Response({'detail': 'Alerta inexistente.'}, status=status.HTTP_404_NOT_FOUND)
            if alerta.estado not in (AlertaState.pendiente, AlertaState.enviada):
                return Response({'detail': 'La alerta ya fue atendida.'}, status=status.HTTP_409_CONFLICT)
            alerta.estado = AlertaState.confirmada if accion == 'enviar_movil' else AlertaState.rechazada
            alerta.motivo_rechazo = motivo if accion == 'rechazar' else None
            alerta.save(update_fields=['estado', 'motivo_rechazo'])
        return Response(AlertaSerializer(alerta).data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAdminRole])
def historico_alertas(request):
    queryset = BotonPanico.objects.all().select_related('created_by', 'lote').order_by('-created_at')
    return Response(AlertaSerializer(queryset, many=True).data)
