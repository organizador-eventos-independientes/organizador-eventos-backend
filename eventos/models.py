from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Límite diario de horas de gestión (US-12).
LIMITE_HORAS_POR_DEFECTO = Decimal('6')
LIMITE_HORAS_MINIMO = 1
LIMITE_HORAS_MAXIMO = 16
LIMITE_FUERA_DE_RANGO = (
    f'El límite debe estar entre {LIMITE_HORAS_MINIMO} y {LIMITE_HORAS_MAXIMO} horas.'
)


class Evento(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    tipo = models.CharField(max_length=100, default='')
    # Con el tipo "otro", cuál es (ej. "Graduación"); vacío con los demás.
    tipo_otro = models.CharField(max_length=40, blank=True, default='')
    cliente = models.CharField(max_length=200, default='')
    # Cómo comunicarse con el cliente (teléfono o correo). Los eventos creados
    # antes de separarlo del cliente lo tienen vacío.
    contacto = models.CharField(max_length=200, default='')
    fecha = models.DateField()
    hora = models.TimeField()
    lugar = models.CharField(max_length=200)
    estado = models.CharField(max_length=20, default='Pendiente')
    # Dueño del evento (US-11). Admite vacío solo por los eventos creados antes
    # del login; la API siempre asigna el usuario autenticado.
    organizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='eventos',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.titulo

class Subtarea(models.Model):
    # Toda gestión nace pendiente y puede pasar a hecha o pospuesta (US-09).
    ESTADO_PENDIENTE = 'Pendiente'
    ESTADO_HECHA = 'Hecha'
    ESTADO_POSPUESTA = 'Pospuesta'

    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_HECHA, 'Hecha'),
        (ESTADO_POSPUESTA, 'Pospuesta'),
    ]

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name='subtareas'
    )
    nombre = models.CharField(max_length=200)
    plazo = models.DateField()
    horas_estimadas = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_PENDIENTE
    )
    nota_estado = models.TextField(blank=True, default='')

    def __str__(self):
        return self.nombre

class ConfiguracionOrganizador(models.Model):
    # Límite de horas de gestión por día, sumando todos los eventos del
    # organizador (US-12). Al reprogramar se avisa si un día lo supera (US-07).
    # Solo existe si el organizador lo guardó; si no, se usa el valor por defecto.
    organizador = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='configuracion'
    )
    limite_horas_diarias = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=LIMITE_HORAS_POR_DEFECTO,
        validators=[
            MinValueValidator(LIMITE_HORAS_MINIMO, LIMITE_FUERA_DE_RANGO),
            MaxValueValidator(LIMITE_HORAS_MAXIMO, LIMITE_FUERA_DE_RANGO),
        ]
    )

    def clean(self):
        # Desde /admin/ rige lo mismo que en la API: el límite no puede quedar
        # por debajo de las horas ya planificadas en algún día. (carga.py
        # importa este módulo, por eso se importa aquí.)
        from .carga import limite_bajo_lo_planificado

        limite = self.limite_horas_diarias
        if self.organizador_id is None or limite is None:
            return
        if not LIMITE_HORAS_MINIMO <= limite <= LIMITE_HORAS_MAXIMO:
            return  # ya lo marcan los validadores del campo
        mensaje = limite_bajo_lo_planificado(self.organizador, limite)
        if mensaje:
            raise ValidationError({'limite_horas_diarias': mensaje})

    def __str__(self):
        return f'Configuración de {self.organizador}'