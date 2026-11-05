from rest_framework import serializers

from .models import BotonPanico, AlertaState
from administracion.serializers import LoteSimpleSerializer, SocioSimpleSerializer
from administracion.models import Lote, Socio


class AlertaValidation(serializers.ModelSerializer):
    """Serializer heredado para validación de alertas; no recibe el socio desde el cliente HTTP."""
    razon = serializers.CharField(max_length=30)
    lote = serializers.PrimaryKeyRelatedField(queryset=Lote.objects.all())
    socio = serializers.PrimaryKeyRelatedField(queryset=Socio.objects.all(), write_only=True)

    class Meta:
        model = BotonPanico
        fields = ['razon', 'lote', 'socio']

    def create(self, validated_data):
        socio = validated_data.pop('socio')
        return BotonPanico.objects.create(created_by=socio, **validated_data)


class AlertaSerializer(serializers.ModelSerializer):
    estado = serializers.ChoiceField(choices=AlertaState.CHOICES, read_only=True)
    razon = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    lote = serializers.SerializerMethodField()
    socio = serializers.SerializerMethodField()

    class Meta:
        model = BotonPanico
        fields = ['id', 'estado', 'razon', 'created_at', 'lote', 'socio', 'motivo_rechazo']

    def get_lote(self, obj):
        if not obj.lote_id:
            return None
        return {'id': obj.lote_id, 'numero': obj.lote.numero}

    def get_socio(self, obj):
        socio = obj.created_by
        if socio is None:
            return None
        return {
            'id': socio.pk,
            'nombre_completo': f'{socio.nombre} {socio.apellido}'.strip(),
            'telefono': socio.telefono,
        }
