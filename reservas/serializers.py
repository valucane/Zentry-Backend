from datetime import datetime
from django.utils import timezone
from rest_framework import serializers
from administracion.models import Socio, Lote
from .models import LugarComun, Reserva


class InstalacionBarrioSerializer(serializers.ModelSerializer):
    """
    Serializer con la estructura exacta de `InstalacionBarrio``.
    """
    id = serializers.CharField(source='codigo')
    duracionMinutos = serializers.IntegerField(source='duracion_minutos', allow_null=True)
    duracionTexto = serializers.SerializerMethodField()
    maxPersonas = serializers.IntegerField(source='max_personas')
    horaApertura = serializers.IntegerField(source='hora_apertura')
    horaCierre = serializers.IntegerField(source='hora_cierre')
    esDiaCompleto = serializers.BooleanField(source='es_dia_completo')
    esCapacidadVariablePorBarrio = serializers.BooleanField(source='es_capacidad_variable')
    tipoAccion = serializers.CharField(source='tipo_accion')

    class Meta:
        model = LugarComun
        fields = [
            'id',
            'nombre',
            'duracionMinutos',
            'duracionTexto',
            'maxPersonas',
            'horaApertura',
            'horaCierre',
            'esDiaCompleto',
            'esCapacidadVariablePorBarrio',
            'tipoAccion',
        ]

    def get_duracionTexto(self, obj):
        if obj.es_dia_completo or not obj.duracion_minutos:
            return 'Todo el día'
        if obj.duracion_minutos == 90:
            return '1:30 hs por turno'
        return f"{obj.horas_turno} hs por turno"


class ReservaSerializer(serializers.ModelSerializer):
    instalacionId = serializers.CharField(write_only=True, required=False)
    instalacionNombre = serializers.CharField(write_only=True, required=False)
    fecha = serializers.CharField(write_only=True, required=False)
    horario = serializers.CharField(write_only=True, required=False)
    cantidadMaximaPersonas = serializers.IntegerField(write_only=True, required=False)
    tipoOperacion = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Reserva
        fields = [
            'id',
            'instalacionId',
            'instalacionNombre',
            'fecha',
            'horario',
            'cantidadMaximaPersonas',
            'tipoOperacion',
            'estado',
        ]
        read_only_fields = ['id', 'estado']

    def to_representation(self, instance):
        es_sum = instance.lugar.codigo == 'sum' or instance.lugar.tipo_accion == 'senar'
        fecha_fmt = instance.fecha_desde.strftime('%d/%m/%Y')
        descripcion = 'SUM reservado' if es_sum else f"{instance.lugar.nombre} reservada"
        detalle = f"Fecha: {fecha_fmt}" if es_sum else f"Fecha: {fecha_fmt} ({instance.horario_texto})"
        lote_str = f"Lote {instance.socio.lote.numero}" if (instance.socio and instance.socio.lote) else "Lote 1"

        return {
            'id': instance.id,
            'hora': timezone.localtime(instance.creada_en).strftime('%H:%M') if instance.creada_en else '12:00',
            'fechaRegistro': instance.creada_en.isoformat() if instance.creada_en else timezone.now().isoformat(),
            'tipo': 'reserva',
            'descripcion': descripcion,
            'ubicacion': lote_str,
            'detalle': detalle,
            'estado': instance.estado,
        }

    def create(self, validated_data):
        raw = self.initial_data
        codigo = raw.get('instalacionId') or 'cancha-tenis'
        nombre = raw.get('instalacionNombre') or 'Instalación'
        fecha_str = raw.get('fecha') or timezone.now().strftime('%Y-%m-%d')
        horario_str = raw.get('horario') or '09:00 - 10:00'
        max_personas = raw.get('cantidadMaximaPersonas') or 4
        tipo_op = raw.get('tipoOperacion') or 'confirmar'

        lugar, _ = LugarComun.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'horas_turno': 1,
                'duracion_minutos': None if codigo == 'sum' else 60,
                'max_personas': max_personas,
                'es_dia_completo': codigo == 'sum',
                'es_capacidad_variable': codigo == 'sum',
                'tipo_accion': tipo_op,
            }
        )

        socio = Socio.objects.first()
        if not socio:
            lote, _ = Lote.objects.get_or_create(numero=1, defaults={'estado': 'ocupado'})
            socio = Socio.objects.create(nombre='Tomás', apellido='Residente', dni='30000000', lote=lote)

        hora_ini = '09:00'
        hora_fin = '23:59'
        if '-' in horario_str and 'Todo' not in horario_str:
            partes = [p.strip() for p in horario_str.split('-')]
            if len(partes) == 2:
                hora_ini = partes[0]
                hora_fin = '23:59' if partes[1] == '00:00' else partes[1]

        try:
            dt_desde = datetime.strptime(f"{fecha_str} {hora_ini}", "%Y-%m-%d %H:%M")
            dt_hasta = datetime.strptime(f"{fecha_str} {hora_fin}", "%Y-%m-%d %H:%M")
            fecha_desde = timezone.make_aware(dt_desde) if timezone.is_naive(dt_desde) else dt_desde
            fecha_hasta = timezone.make_aware(dt_hasta) if timezone.is_naive(dt_hasta) else dt_hasta
        except ValueError:
            fecha_desde = timezone.now()
            fecha_hasta = timezone.now()

        estado = 'pendiente' if tipo_op == 'senar' else 'aprobado'

        return Reserva.objects.create(
            socio=socio,
            lugar=lugar,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            horario_texto=horario_str,
            estado=estado,
        )
