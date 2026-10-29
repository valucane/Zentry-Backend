import secrets

from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction

from .models import Lote, PuntoAcceso, Socio, Administrador, Guardia, Proveedor, Account

class LoteSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Lote
        fields = ['id', 'numero', 'estado']

class LoteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Lote
        fields = ['id', 'numero', 'estado']

class PuntoAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntoAcceso
        fields = ['id', 'nombre', 'tipo', 'estado']

class SocioSimpleSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Socio
        fields = ['id', 'nombre_completo', 'telefono', 'tipo']

    def get_nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}".strip()
    
class SocioSerializer(serializers.ModelSerializer):
    lote_numero = serializers.IntegerField(write_only=True, required=False)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    tiene_acceso = serializers.SerializerMethodField(read_only=True)
    lote = serializers.SerializerMethodField(read_only=True)
    nombre_completo = serializers.SerializerMethodField(read_only=True)
    rolPropiedad = serializers.CharField(source='rol_propiedad', required=False)
    fechaInicioContrato = serializers.DateField(source='fecha_inicio_contrato', required=False, allow_null=True)
    fechaFinContrato = serializers.DateField(source='fecha_fin_contrato', required=False, allow_null=True)

    class Meta:
        model = Socio
        fields = [
            'id',
            'nombre',
            'apellido',
            'nombre_completo',
            'dni',
            'email',
            'password',
            'tiene_acceso',
            'telefono',
            'tipo',
            'lote',
            'lote_numero',
            'rolPropiedad',
            'patentes',
            'fechaInicioContrato',
            'fechaFinContrato',
            'is_active',
        ]

    def get_lote(self, obj):
        return obj.lote.numero if obj.lote else 1

    def get_nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}".strip()

    def get_tiene_acceso(self, obj):
        return bool(
            obj.account_id
            and obj.account.is_active
            and obj.account.user.is_active
        )

    def validate_email(self, value):
        users = User.objects.filter(email__iexact=value)
        if self.instance and self.instance.account_id:
            users = users.exclude(pk=self.instance.account.user_id)
        if users.exists():
            raise serializers.ValidationError(
                'Ya existe una cuenta con este correo electrónico.'
            )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({
                'password': 'La contraseña inicial es obligatoria.'
            })
        if self.instance and not self.instance.account_id and not attrs.get('password'):
            raise serializers.ValidationError({
                'password': 'Definí una contraseña para habilitar el acceso de este residente.'
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        lote_num = validated_data.pop('lote_numero', None)
        password = validated_data.pop('password')
        if lote_num is None and 'lote' in self.initial_data:
            raw_lote = str(self.initial_data.get('lote', '')).replace('Lote', '').strip()
            if raw_lote.isdigit():
                lote_num = int(raw_lote)
        if lote_num:
            lote_obj, _ = Lote.objects.get_or_create(numero=lote_num, defaults={'estado': 'ocupado'})
            validated_data['lote'] = lote_obj

        email = validated_data['email']
        user = User(
            username=f'residente_{secrets.token_hex(16)}',
            email=email,
            first_name=validated_data.get('nombre', ''),
            last_name=validated_data.get('apellido', ''),
        )
        user.set_password(password)
        user.save()
        account = Account.objects.create(user=user, role='socio')
        validated_data['account'] = account
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        lote_num = validated_data.pop('lote_numero', None)
        password = validated_data.pop('password', None)
        if lote_num is None and 'lote' in self.initial_data:
            raw_lote = str(self.initial_data.get('lote', '')).replace('Lote', '').strip()
            if raw_lote.isdigit():
                lote_num = int(raw_lote)
        if lote_num:
            lote_obj, _ = Lote.objects.get_or_create(numero=lote_num, defaults={'estado': 'ocupado'})
            validated_data['lote'] = lote_obj
        socio = super().update(instance, validated_data)
        if socio.account_id:
            user = socio.account.user
        else:
            user = User(
                username=f'residente_{secrets.token_hex(16)}',
                email=socio.email,
            )
            user.save()
            socio.account = Account.objects.create(user=user, role='socio')
            socio.save(update_fields=['account'])

        user.email = socio.email
        user.first_name = socio.nombre
        user.last_name = socio.apellido
        if password:
            user.set_password(password)
            user.is_active = True
            socio.account.is_active = True
            socio.account.save(update_fields=['is_active'])
        user.save()
        return socio


class AdministradorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Administrador
        fields = ['id', 'nombre', 'dni', 'email', 'password', 'is_active']
        read_only_fields = ['id', 'is_active']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'Ya existe una cuenta con este correo electrónico.'
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data['email']
        user = User(
            username=f'administrador_{secrets.token_hex(16)}',
            email=email,
            first_name=validated_data['nombre'],
        )
        user.set_password(password)
        user.save()
        validated_data['account'] = Account.objects.create(user=user, role='admin')
        return super().create(validated_data)


class GuardiaSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = Guardia
        fields = ['id', 'nombre', 'email', 'password', 'is_active']
        read_only_fields = ['is_active']

    def validate_email(self, value):
        users = User.objects.filter(email__iexact=value)
        if self.instance and self.instance.account_id:
            users = users.exclude(pk=self.instance.account.user_id)
        if users.exists():
            raise serializers.ValidationError(
                'Ya existe una cuenta con este correo electrónico.'
            )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({
                'password': 'La contraseña inicial es obligatoria.'
            })
        if self.instance and not self.instance.account_id and not attrs.get('password'):
            raise serializers.ValidationError({
                'password': 'Definí una contraseña para habilitar el acceso de este guardia.'
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.setdefault('dni', '')
        email = validated_data['email']
        user = User(
            username=f'guardia_{secrets.token_hex(16)}',
            email=email,
            first_name=validated_data.get('nombre', ''),
        )
        user.set_password(password)
        user.save()
        validated_data['account'] = Account.objects.create(user=user, role='guardia')
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        guardia = super().update(instance, validated_data)

        if guardia.account_id:
            user = guardia.account.user
        else:
            user = User(
                username=f'guardia_{secrets.token_hex(16)}',
                email=guardia.email,
            )
            user.save()
            guardia.account = Account.objects.create(user=user, role='guardia')
            guardia.save(update_fields=['account'])

        user.email = guardia.email
        user.first_name = guardia.nombre
        if password:
            user.set_password(password)
        user.save()
        return guardia
