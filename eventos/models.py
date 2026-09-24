from django.db import models


class Evento(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    tipo = models.CharField(max_length=100, default='')
    cliente = models.CharField(max_length=200, default='')
    fecha = models.DateField()
    hora = models.TimeField()
    lugar = models.CharField(max_length=200)
    estado = models.CharField(max_length=20, default='Pendiente')

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