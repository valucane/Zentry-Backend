import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from administracion.models import Account


class Command(BaseCommand):
    help = 'Crea o actualiza la cuenta de administrador configurada por entorno.'

    def handle(self, *args, **options):
        email = os.environ.get('ZENTRY_ADMIN_EMAIL', '').strip()
        password = os.environ.get('ZENTRY_ADMIN_PASSWORD', '')
        if not email or not password:
            raise CommandError(
                'Definí ZENTRY_ADMIN_EMAIL y ZENTRY_ADMIN_PASSWORD en el entorno.'
            )

        users = list(User.objects.filter(email__iexact=email)[:2])
        if len(users) > 1:
            raise CommandError(
                'Hay más de un usuario con ese email; resolvé el duplicado antes de continuar.'
            )

        if users:
            user = users[0]
        else:
            if User.objects.filter(username__iexact=email).exists():
                raise CommandError(
                    'El email ya está usado como nombre de usuario por otra cuenta.'
                )
            user = User(username=email, email=email)

        user.email = email
        user.is_active = True
        user.set_password(password)
        user.save()
        Account.all_objects.update_or_create(
            user=user,
            defaults={'role': 'admin', 'is_active': True},
        )

        self.stdout.write(self.style.SUCCESS(
            f'Cuenta de administrador configurada para {email}.'
        ))
