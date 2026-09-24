from rest_framework import serializers
from .models import Evento, Subtarea

class EventoSerializer(serializers.ModelSerializer):
    titulo = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El título del evento es obligatorio.',
            'blank': 'El título del evento es obligatorio.'
        }
    )

    descripcion = serializers.CharField(
        required=False,
        allow_blank=True,
        error_messages={
            'blank': 'La descripción del evento no puede ser inválida.'
        }
    )

    tipo = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El tipo de evento es obligatorio.',
            'blank': 'El tipo de evento es obligatorio.'
        }
    )

    cliente = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El cliente o contacto es obligatorio.',
            'blank': 'El cliente o contacto es obligatorio.'
        }
    )

    fecha = serializers.DateField(
        required=True,
        error_messages={
            'required': 'La fecha del evento es obligatoria.',
            'invalid': 'La fecha debe tener un formato válido.'
        }
    )

    hora = serializers.TimeField(
        required=True,
        error_messages={
            'required': 'La hora del evento es obligatoria.',
            'invalid': 'La hora del evento debe tener un formato válido.'
        }
    )

    lugar = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El lugar del evento es obligatorio.',
            'blank': 'El lugar del evento es obligatorio.'
        }
    )

    class Meta:
        model = Evento
        fields = '__all__'


class SubtareaSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El nombre de la subtarea es obligatorio.',
            'blank': 'El nombre de la subtarea es obligatorio.'
        }
    )

    plazo = serializers.DateField(
        required=True,
        error_messages={
            'required': 'El plazo de la subtarea es obligatorio.',
            'invalid': 'El plazo debe tener un formato de fecha válido.'
        }
    )

    horas_estimadas = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=True,
        error_messages={
            'required': 'Las horas estimadas son obligatorias.',
            'invalid': 'Las horas estimadas deben ser un número válido.'
        }
    )

    class Meta:
        model = Subtarea
        fields = '__all__'
        extra_kwargs = {
            'evento': {'required': False}
        }

    def validate_horas_estimadas(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Las horas estimadas deben ser mayores que 0.'
            )
        return value