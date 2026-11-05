import os
import secrets

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from administracion.models import Account, Socio


class Command(BaseCommand):
    help = 'Configura el acceso de un residente ya registrado.'

    @transaction.atomic
    def handle(self, *args, **options):
        email = os.environ.get('ZENTRY_RESIDENT_EMAIL', '').strip()
        password = os.environ.get('ZENTRY_RESIDENT_PASSWORD', '')
        if not email or not password:
            raise CommandError(
                'Definí ZENTRY_RESIDENT_EMAIL y ZENTRY_RESIDENT_PASSWORD en el entorno.'
            )
        if len(password) < 8:
            raise CommandError('La contraseña debe tener al menos 8 caracteres.')

        socios = list(Socio.all_objects.filter(email__iexact=email)[:2])
        if len(socios) != 1:
            raise CommandError(
                'Debe existir exactamente un residente registrado con ese email.'
            )
        socio = socios[0]

        users = list(User.objects.filter(email__iexact=email)[:2])
        if len(users) > 1:
            raise CommandError(
                'Hay más de un usuario con ese email; resolvé el duplicado primero.'
            )
        user = users[0] if users else None

        account = socio.account if socio.account_id else None
        if account and account.role != 'socio':
            raise CommandError(
                'El residente está vinculado a una cuenta que no tiene rol socio.'
            )
        if account and account.user.email.casefold() != email.casefold():
            raise CommandError(
                'El residente ya tiene una cuenta con otro email.'
            )
        if user and (user.is_superuser or user.is_staff):
            raise CommandError(
                'El email pertenece a una cuenta administrativa y no se puede asignar al residente.'
            )
        user_account = Account.all_objects.filter(user=user).first() if user else None
        if user_account:
            if user_account.role != 'socio' or (account and account.pk != user_account.pk):
                raise CommandError(
                    'El email ya está vinculado a otra cuenta o perfil.'
                )
            account = user_account
        elif account and user and account.user_id != user.pk:
            raise CommandError(
                'El residente ya tiene una cuenta con otro email.'
            )

        if user is None:
            user = User(
                username=f'residente_{secrets.token_hex(16)}',
                email=email,
            )
        user.email = email
        user.first_name = socio.nombre
        user.last_name = socio.apellido
        user.is_active = True
        user.set_password(password)
        user.save()

        if account is None:
            account = Account.all_objects.create(
                user=user,
                role='socio',
                is_active=True,
            )
        else:
            account.is_active = True
            account.save(update_fields=['is_active'])

        if socio.account_id != account.pk:
            socio.account = account
            socio.save(update_fields=['account'])

        self.stdout.write(self.style.SUCCESS(
            f'Acceso de residente configurado para {email}.'
        ))
