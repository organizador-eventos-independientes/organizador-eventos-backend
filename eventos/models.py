from decimal import Decimal

from django.conf import settings
from django.db import models

LIMITE_HORAS_POR_DEFECTO = Decimal('6')


class Evento(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    tipo = models.CharField(max_length=100, default='')
    cliente = models.CharField(max_length=200, default='')
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
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name='subtareas'
    )
    nombre = models.CharField(max_length=200)
    plazo = models.DateField()
    horas_estimadas = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return self.nombre


class ConfiguracionOrganizador(models.Model):
    # Límite de horas de gestión por día, sumando todos los eventos del
    # organizador (US-12). Al reprogramar se avisa si un día lo supera (US-07).
    # Se crea con el valor por defecto la primera vez que se consulta.
    organizador = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='configuracion'
    )
    limite_horas_diarias = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=LIMITE_HORAS_POR_DEFECTO
    )

    def __str__(self):
        return f'Configuración de {self.organizador}'