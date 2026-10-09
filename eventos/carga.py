from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from .models import ConfiguracionOrganizador, Subtarea


def configuracion_de(organizador):
    # Si el organizador nunca guardó su límite, se usa uno sin guardar con el
    # valor por defecto (6 h); se guarda la primera vez que lo cambia.
    return (
        ConfiguracionOrganizador.objects.filter(organizador=organizador).first()
        or ConfiguracionOrganizador(organizador=organizador)
    )


# Las horas se guardan con dos decimales, pero son horas y minutos de reloj
# (2:45 = 2.75; 2:20 = 2.33). Las cuentas se hacen en minutos enteros para que
# los redondeos no se acumulen (tres gestiones de 0:40 suman 2 h, no 2,01).
def a_minutos(horas):
    # 2.75 -> 165; 2.33 -> 140
    return round(Decimal(horas) * 60)


def a_horas(minutos):
    # 165 -> 2.75; 140 -> 2.33
    return (Decimal(minutos) / 60).quantize(Decimal('0.01'))


def duracion_texto(minutos):
    # 420 -> "7"; 450 -> "7:30"
    horas, resto = divmod(minutos, 60)
    return f'{horas}:{resto:02d}' if resto else str(horas)


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
    limite_min = a_minutos(limite)
    planificadas_min = sum(a_minutos(s.horas_estimadas) for s in del_dia)
    gestion_min = a_minutos(horas)
    total_min = planificadas_min + gestion_min
    if total_min <= limite_min:
        return None

    return {
        'mensaje': (
            f'Quedarías con {duracion_texto(total_min)}h de gestión planificadas '
            f'(límite {duracion_texto(limite_min)}h)'
        ),
        'fecha': plazo,
        'limite': limite,
        'planificadas': a_horas(planificadas_min),
        'horas_gestion': horas,
        'total': a_horas(total_min),
        # Para "reducir horas": lo máximo que cabe ese día.
        'horas_disponibles': a_horas(max(limite_min - planificadas_min, 0)),
        'siguiente_dia_disponible': siguiente_dia_con_espacio(
            otras, plazo, gestion_min, limite_min, subtarea.evento.fecha
        ),
        'gestiones_del_dia': del_dia,
    }


def siguiente_dia_con_espacio(otras, desde, minutos, limite_min, hasta):
    # Para "posponer": el primer día después de `desde` en el que la gestión
    # (`minutos`) cabe, sin pasar de `hasta` (la fecha del evento). Si sola ya
    # supera el límite o no queda espacio antes del evento, ningún día sirve.
    if minutos > limite_min:
        return None

    ocupados = defaultdict(int)
    for dia, horas in otras.filter(plazo__gt=desde, plazo__lte=hasta).values_list('plazo', 'horas_estimadas'):
        ocupados[dia] += a_minutos(horas)
    dia = desde + timedelta(days=1)
    while dia <= hasta:
        if ocupados[dia] + minutos <= limite_min:
            return dia
        dia += timedelta(days=1)
    return None
