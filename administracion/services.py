from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.db import transaction

from .models import Account

@transaction.atomic
def deactivate_account(account:Account):
    if not account.is_active:
        raise ValueError("La cuenta ya se encuentra desactivada")
    user = User.objects.get(id=account.user.id)
    try:
        token = Token.objects.get(user=user)
        if token:
            token.delete()
    except Token.DoesNotExist:
        pass
    
    user.is_active = False
    user.save()
    account.is_active = False
    account.save()
    
    return

@transaction.atomic
def activate_account(account: Account) -> Account:
    if account.is_active:
        raise ValueError("No se puede activar una cuenta que ya esta activa")
    user = User.objects.get(id=account.user.id)
    user.is_active = True
    user.save()
    account.is_active = True
    account.save()
    
    Token.objects.get_or_create(user=user)
    
    return account