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


def dias_sobre_limite(organizador, limite):
    """US-12: los días en que las gestiones del organizador (sumando todos sus
    eventos) ya pasan de `limite`, como pares (día, minutos planificados), del
    más antiguo al más lejano. Cuentan todos los días, también los vencidos."""
    limite_min = a_minutos(limite)
    por_dia = defaultdict(int)
    gestiones = Subtarea.objects.filter(evento__organizador=organizador)
    for dia, horas in gestiones.values_list('plazo', 'horas_estimadas'):
        por_dia[dia] += a_minutos(horas)
    return [(dia, minutos) for dia, minutos in sorted(por_dia.items()) if minutos > limite_min]


def limite_bajo_lo_planificado(organizador, limite):
    """US-12: el límite diario no puede quedar por debajo de lo que ya está
    planificado en ningún día (llegar justo al límite sí se permite). Devuelve
    el mensaje de error con los días que lo impiden, o None si el límite cabe."""
    dias = dias_sobre_limite(organizador, limite)
    if not dias:
        return None

    limite_texto = duracion_texto(a_minutos(limite))
    if len(dias) == 1:
        dia, minutos = dias[0]
        donde = f'el {dia:%d/%m/%Y} ya tienes {duracion_texto(minutos)}h de gestión planificadas'
    else:
        # Se nombran los tres primeros días; el resto solo se cuenta.
        donde = ', '.join(f'{dia:%d/%m/%Y} ({duracion_texto(minutos)}h)' for dia, minutos in dias[:3])
        restantes = len(dias) - 3
        if restantes > 0:
            donde += f' y {restantes} {"día" if restantes == 1 else "días"} más'
        donde = f'ya tienes más horas de gestión planificadas los días {donde}'
    return (
        f'No puedes cambiar el límite a {limite_texto}h: {donde}. '
        'Reprograma o reduce esas gestiones primero.'
    )


def sobrecarga_al_guardar(organizador, subtarea, plazo, horas):
    """Al crear o editar una gestión: si con ella (en `plazo`, con `horas`) ese
    día pasa del límite diario del organizador (sumando todos sus eventos),
    devuelve los errores para el formulario: un mensaje general y uno corto para
    el campo que conviene cambiar. Si cabe, devuelve None. `subtarea` es la que
    se edita (no se cuenta dos veces) o None al crearla."""
    gestiones = Subtarea.objects.filter(evento__organizador=organizador, plazo=plazo)
    if subtarea is not None:
        gestiones = gestiones.exclude(pk=subtarea.pk)
    planificadas_min = sum(a_minutos(h) for h in gestiones.values_list('horas_estimadas', flat=True))
    limite_min = a_minutos(configuracion_de(organizador).limite_horas_diarias)
    total_min = planificadas_min + a_minutos(horas)
    if total_min <= limite_min:
        return None

    disponibles_min = max(limite_min - planificadas_min, 0)
    resumen = (
        f'Quedarías con {duracion_texto(total_min)}h de gestión planificadas el {plazo:%d/%m/%Y} '
        f'(límite {duracion_texto(limite_min)}h)'
    )
    planificadas = duracion_texto(planificadas_min)
    if planificadas_min == 0:
        return {
            'general': f'{resumen}: esta gestión sola pasa de tu límite diario. Reduce las horas estimadas.',
            'horas_estimadas': f'Pasa de tu límite diario de {duracion_texto(limite_min)}h.',
        }
    if disponibles_min == 0:
        return {
            'general': f'{resumen}: ese día ya tienes {planificadas}h y no cabe nada más. Elige otro plazo.',
            'plazo': 'Ese día ya llegó a tu límite diario.',
        }
    disponibles = duracion_texto(disponibles_min)
    return {
        'general': (
            f'{resumen}: ese día ya tienes {planificadas}h. '
            f'Reduce las horas a {disponibles}h o elige otro plazo.'
        ),
        'horas_estimadas': f'Ese día solo caben {disponibles}h más.',
    }


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
