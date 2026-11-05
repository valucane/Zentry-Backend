class AlertaState:
    pendiente = 'pendiente'
    enviada = 'enviada'
    rechazada = 'rechazada'
    confirmada = 'confirmada'

    CHOICES = (
        (pendiente, 'Pendiente'),
        (enviada, 'Enviada'),
        (rechazada, 'Rechazada'),
        (confirmada, 'Confirmada')
    )