from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum

from .models import ConfiguracionOrganizador, Subtarea


def configuracion_de(organizador):
    # Si el organizador nunca guardó su límite, se usa uno sin guardar con el
    # valor por defecto (6 h); se guarda la primera vez que lo cambia.
    return (
        ConfiguracionOrganizador.objects.filter(organizador=organizador).first()
        or ConfiguracionOrganizador(organizador=organizador)
    )


def horas_texto(horas):
    # 7.00 -> "7", 7.50 -> "7,5"
    return format(Decimal(horas).normalize(), 'f').replace('.', ',')


def detectar_sobrecarga(organizador, subtarea, plazo, horas):
    """US-07: si al dejar `subtarea` en `plazo` con `horas` ese día supera el
    límite diario del organizador (sumando todos sus eventos), devuelve el
    conflicto con lo necesario para resolverlo; si cabe, devuelve None."""
    limite = configuracion_de(organizador).limite_horas_diarias
    otras = Subtarea.objects.filter(evento__organizador=organizador).exclude(pk=subtarea.pk)
    del_dia = list(
        otras.filter(plazo=plazo)
        .select_related('evento')
        .order_by('horas_estimadas', 'nombre')
    )
    # Un día sin gestiones empieza en 0 h.
    planificadas = sum((s.horas_estimadas for s in del_dia), Decimal('0'))
    total = planificadas + horas
    if total <= limite:
        return None

    return {
        'mensaje': (
            f'Quedarías con {horas_texto(total)}h de gestión planificadas '
            f'(límite {horas_texto(limite)}h)'
        ),
        'fecha': plazo,
        'limite': limite,
        'planificadas': planificadas,
        'horas_gestion': horas,
        'total': total,
        # Para "reducir horas": lo máximo que cabe ese día.
        'horas_disponibles': max(limite - planificadas, Decimal('0')),
        'siguiente_dia_disponible': siguiente_dia_con_espacio(
            otras, plazo, horas, limite, subtarea.evento.fecha
        ),
        'gestiones_del_dia': del_dia,
    }


def siguiente_dia_con_espacio(otras, desde, horas, limite, hasta):
    # Para "posponer": el primer día después de `desde` en el que la gestión
    # cabe, sin pasar de `hasta` (la fecha del evento). Si sola ya supera el
    # límite o no queda espacio antes del evento, ningún día sirve.
    if horas > limite:
        return None

    ocupadas = dict(
        otras.filter(plazo__gt=desde)
        .order_by()
        .values('plazo')
        .annotate(horas=Sum('horas_estimadas'))
        .values_list('plazo', 'horas')
    )
    dia = desde + timedelta(days=1)
    while dia <= hasta:
        if ocupadas.get(dia, 0) + horas <= limite:
            return dia
        dia += timedelta(days=1)
    return None
