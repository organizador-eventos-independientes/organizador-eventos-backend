from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db import IntegrityError
from django.utils import timezone, translation
from rest_framework import serializers
from .models import Evento, Subtarea

User = get_user_model()

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
        read_only_fields = ['organizador']


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

    def get_fields(self):
        fields = super().get_fields()
        # Una gestión solo puede asociarse a eventos del organizador autenticado;
        # el id de un evento ajeno se rechaza igual que uno inexistente.
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated:
            fields['evento'].queryset = Evento.objects.filter(organizador=request.user)
        return fields

    def validate_horas_estimadas(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Las horas estimadas deben ser mayores que 0.'
            )
        return value


class ReprogramarSubtareaSerializer(serializers.ModelSerializer):
    # US-06: solo cambia la fecha objetivo; el resto de la gestión no se toca.
    plazo = serializers.DateField(
        required=True,
        error_messages={
            'required': 'La nueva fecha objetivo es obligatoria.',
            'null': 'La nueva fecha objetivo es obligatoria.',
            'invalid': 'La fecha objetivo debe tener un formato de fecha válido.'
        }
    )

    class Meta:
        model = Subtarea
        fields = ['plazo']

    def validate_plazo(self, value):
        # Se puede mover una gestión vencida, pero no a una fecha ya pasada.
        if value < timezone.localdate():
            raise serializers.ValidationError(
                'La fecha objetivo no puede ser anterior a hoy.'
            )
        return value


class HoyFiltrosSerializer(serializers.Serializer):
    evento = serializers.PrimaryKeyRelatedField(
        queryset=Evento.objects.none(),
        required=False,
        error_messages={
            'does_not_exist': 'El evento no existe.',
            'incorrect_type': 'El evento debe indicarse con su id.'
        }
    )

    estado = serializers.ChoiceField(
        choices=['vencidas', 'hoy', 'proximas'],
        required=False,
        error_messages={
            'invalid_choice': 'El estado debe ser vencidas, hoy o proximas.'
        }
    )

    dias = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text='Solo limita las próximas: las que vencen en los próximos N días.',
        error_messages={
            'invalid': 'Los días deben ser un número entero.',
            'min_value': 'Los días deben ser mayores que 0.'
        }
    )

    def get_fields(self):
        fields = super().get_fields()
        # Un evento ajeno se rechaza igual que uno inexistente.
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated:
            fields['evento'].queryset = Evento.objects.filter(organizador=request.user)
        return fields


class SubtareaHoySerializer(serializers.ModelSerializer):
    evento_titulo = serializers.CharField(source='evento.titulo', read_only=True)

    class Meta:
        model = Subtarea
        fields = ['id', 'evento', 'evento_titulo', 'nombre', 'plazo', 'horas_estimadas']


class HoyRespuestaSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    vencidas = SubtareaHoySerializer(many=True)
    hoy = SubtareaHoySerializer(many=True)
    proximas = SubtareaHoySerializer(many=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        trim_whitespace=False,
        style={'input_type': 'password'}
    )


USUARIO_EN_USO = 'Ese nombre de usuario ya está en uso. Elige otro.'


class RegistroSerializer(serializers.Serializer):
    nombre = serializers.CharField(
        max_length=150,
        error_messages={
            'required': 'Escribe tu nombre.',
            'blank': 'Escribe tu nombre.',
            'max_length': 'El nombre no puede superar 150 caracteres.'
        }
    )

    username = serializers.CharField(
        max_length=150,
        validators=[RegexValidator(
            r'^[\w.@+-]+\Z',
            'El usuario solo puede tener letras, números y los signos @ . + - _ (sin espacios).'
        )],
        error_messages={
            'required': 'Escribe un nombre de usuario.',
            'blank': 'Escribe un nombre de usuario.',
            'max_length': 'El usuario no puede superar 150 caracteres.'
        }
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'},
        error_messages={
            'required': 'Escribe una contraseña.',
            'blank': 'Escribe una contraseña.'
        }
    )

    def validate_username(self, value):
        value = User.normalize_username(value)
        # Sin distinguir mayúsculas, para que no existan "Ana" y "ana" a la vez.
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(USUARIO_EN_USO)
        return value

    def validate(self, attrs):
        nombre, _, apellido = attrs['nombre'].partition(' ')
        usuario = User(username=attrs['username'], first_name=nombre, last_name=apellido.strip())

        # Mismas reglas de contraseña que el resto de Django
        # (AUTH_PASSWORD_VALIDATORS), con los mensajes en español.
        with translation.override('es'):
            try:
                password_validation.validate_password(attrs['password'], usuario)
            except DjangoValidationError as error:
                raise serializers.ValidationError({'password': list(error.messages)})

        attrs['usuario'] = usuario
        return attrs

    def create(self, validated_data):
        usuario = validated_data['usuario']
        usuario.set_password(validated_data['password'])
        try:
            usuario.save()
        except IntegrityError:
            # Otro registro tomó el mismo usuario justo al mismo tiempo.
            raise serializers.ValidationError({'username': [USUARIO_EN_USO]})
        return usuario


class UsuarioSesionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    nombre = serializers.CharField()


class LoginRespuestaSerializer(serializers.Serializer):
    token = serializers.CharField()
    usuario = UsuarioSesionSerializer()