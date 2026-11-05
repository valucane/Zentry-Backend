import unicodedata

from django.core import signing


QR_TOKEN_SALT = 'invitaciones.qr'

DIAS_SEMANA = {
    'lunes': 0,
    'martes': 1,
    'miercoles': 2,
    'jueves': 3,
    'viernes': 4,
    'sabado': 5,
    'domingo': 6,
}


def crear_token_qr(invitacion_id):
    return signing.dumps(
        {'invitacion_id': invitacion_id},
        salt=QR_TOKEN_SALT,
    )


def obtener_id_invitacion(token):
    try:
        payload = signing.loads(token, salt=QR_TOKEN_SALT)
    except signing.BadSignature:
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return int(payload['invitacion_id'])
    except (KeyError, TypeError, ValueError):
        return None


def obtener_dia_semana(dia):
    normalizado = unicodedata.normalize('NFD', dia.casefold())
    normalizado = ''.join(
        caracter
        for caracter in normalizado
        if not unicodedata.combining(caracter)
    )
    return DIAS_SEMANA.get(normalizado.strip())
