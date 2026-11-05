from datetime import datetime
from django.utils import timezone
from rest_framework import serializers
from administracion.models import PuntoAcceso, Socio, Lote
from .models import Invitado, Invitacion, InvitacionHistorico, RegistroAcceso
from .qr import crear_token_qr, obtener_dia_semana


class InvitacionFrontendSerializer(serializers.ModelSerializer):
    """
    Serializer adaptado exactamente a la interfaz `Invitacion` de Angular (`invitacion-storage.service.ts`).
    """
    id = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()
    nombreVisitante = serializers.CharField(write_only=True, required=False)
    dni = serializers.CharField(write_only=True, required=False)
    porton = serializers.CharField(write_only=True, required=False, allow_blank=True)
    fechaInicio = serializers.CharField(write_only=True, required=False, allow_blank=True)
    fechaFin = serializers.CharField(write_only=True, required=False, allow_blank=True)
    dias = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = Invitacion
        fields = [
            'id',
            'tipo',
            'nombreVisitante',
            'dni',
            'porton',
            'fechaInicio',
            'fechaFin',
            'dias',
        ]

    def get_id(self, obj):
        return str(obj.id)

    def get_tipo(self, obj):
        # El frontend usa 'concurrente' para las recurrentes
        return 'concurrente' if obj.tipo == 'recurrente' else 'unica'

    def to_representation(self, instance):
        nombre_completo = f"{instance.invitado.nombre} {instance.invitado.apellido}".strip()
        return {
            'id': str(instance.id),
            'qrToken': crear_token_qr(instance.pk),
            'tipo': 'concurrente' if instance.tipo == 'recurrente' else 'unica',
            'nombreVisitante': nombre_completo,
            'dni': instance.invitado.dni,
            'porton': instance.punto_acceso.nombre if instance.punto_acceso else 'Portón Principal',
            'fechaInicio': instance.fecha_inicio.strftime('%Y-%m-%d') if instance.fecha_inicio else None,
            'fechaFin': instance.fecha_visita.strftime('%Y-%m-%d') if instance.fecha_visita else None,
            'dias': instance.dias_semana or [],
            'creadaEn': instance.fecha_creacion.isoformat() if instance.fecha_creacion else timezone.now().isoformat(),
            'usadaEn': instance.usada_en.isoformat() if instance.usada_en else None,
        }

    def validate(self, attrs):
        raw = self.initial_data
        tipo = raw.get('tipo', 'unica')
        if tipo not in ('unica', 'concurrente', 'recurrente'):
            raise serializers.ValidationError(
                {'tipo': 'El tipo debe ser unica o concurrente.'}
            )

        dias = raw.get('dias') or []
        if tipo in ('concurrente', 'recurrente') and not dias:
            raise serializers.ValidationError(
                {'dias': 'Debe seleccionar al menos un dia para una invitacion recurrente.'}
            )
        if tipo in ('concurrente', 'recurrente') and any(
            not isinstance(dia, str) or obtener_dia_semana(dia) is None
            for dia in dias
        ):
            raise serializers.ValidationError(
                {'dias': 'Los dias deben ser nombres validos de la semana.'}
            )

        fechas = {}
        for campo in ('fechaInicio', 'fechaFin'):
            valor = raw.get(campo)
            if not valor:
                continue
            try:
                fechas[campo] = datetime.strptime(valor, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    {campo: 'La fecha debe tener el formato AAAA-MM-DD.'}
                )

        if (
            'fechaInicio' in fechas
            and 'fechaFin' in fechas
            and fechas['fechaFin'] < fechas['fechaInicio']
        ):
            raise serializers.ValidationError(
                {'fechaFin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'}
            )

        return attrs

    def create(self, validated_data):
        raw = self.initial_data
        nombre_visitante = (raw.get('nombreVisitante') or '').strip()
        partes = nombre_visitante.split(' ', 1)
        nombre = partes[0] if partes else 'Visitante'
        apellido = partes[1] if len(partes) > 1 else ''
        dni = (raw.get('dni') or '').strip()
        porton_nombre = (raw.get('porton') or 'Portón Principal').strip()
        tipo_front = raw.get('tipo', 'unica')
        tipo_db = 'recurrente' if tipo_front in ('concurrente', 'recurrente') else 'unica'
        dias = raw.get('dias') or []

        invitado, _ = Invitado.all_objects.update_or_create(
            dni=dni,
            defaults={'nombre': nombre, 'apellido': apellido, 'is_active': True}
        )

        punto_acceso, _ = PuntoAcceso.objects.get_or_create(
            nombre=porton_nombre,
            defaults={'tipo': 'mixto', 'estado': 'abierto'}
        )

        socio = Socio.objects.first()
        if not socio:
            lote, _ = Lote.objects.get_or_create(numero=1, defaults={'estado': 'ocupado'})
            socio = Socio.objects.create(nombre='Tomás', apellido='Residente', dni='30000000', lote=lote)

        ahora = timezone.now()
        fecha_inicio = ahora
        fecha_visita = ahora

        if raw.get('fechaInicio'):
            fecha_inicio = timezone.make_aware(
                datetime.combine(
                    datetime.strptime(raw['fechaInicio'], '%Y-%m-%d').date(),
                    datetime.min.time(),
                )
            )

        if raw.get('fechaFin'):
            fecha_visita = timezone.make_aware(
                datetime.combine(
                    datetime.strptime(raw['fechaFin'], '%Y-%m-%d').date(),
                    datetime.min.time(),
                )
            )

        invitacion = Invitacion.objects.create(
            invitado=invitado,
            socio=socio,
            punto_acceso=punto_acceso,
            fecha_inicio=fecha_inicio,
            fecha_visita=fecha_visita,
            dias_habilitados=len(dias) if dias else 1,
            dias_semana=dias,
            tipo=tipo_db,
        )
        return invitacion
