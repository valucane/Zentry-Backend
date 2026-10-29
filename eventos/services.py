import json
import time

from django.db import close_old_connections

from .models import BotonPanico, AlertaState


def eventos():
    yield ': ok\n\n'
    while True:
        close_old_connections()
        alertas = BotonPanico.objects.filter(
            estado=AlertaState.pendiente,
        ).select_related('socio').order_by('id')
        if not alertas:
            yield ': ping\n\n'
        for alerta in alertas:
            data = json.dumps({
                'alerta_id': alerta.id,
                'nro_lote': alerta.lote,
                'telefono': alerta.created_by.telefono,
                'razon': alerta.razon,
                'nombre': alerta.created_by.nombre_completo(),
            })
            alerta.estado = AlertaState.enviada
            alerta.save()
            yield f'data: {data}\n\n'
        time.sleep(1)
