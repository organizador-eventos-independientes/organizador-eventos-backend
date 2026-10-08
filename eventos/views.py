from datetime import timedelta

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Evento, Subtarea
from .serializers import (
    EventoSerializer,
    HoyFiltrosSerializer,
    HoyRespuestaSerializer,
    LoginRespuestaSerializer,
    LoginSerializer,
    RegistroSerializer,
    ReprogramarSubtareaSerializer,
    SubtareaHoySerializer,
    SubtareaSerializer,
)


def datos_sesion(user, token):
    return {
        'token': token.key,
        'usuario': {
            'id': user.id,
            'username': user.username,
            'nombre': user.get_full_name() or user.username,
        },
    }


class LoginView(APIView):
    # El login no exige token (e ignora uno viejo que envíe el cliente).
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: LoginRespuestaSerializer,
            400: OpenApiResponse(description='Credenciales inválidas.'),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        user = None
        if serializer.is_valid():
            user = authenticate(
                request,
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )

        if user is None:
            # Mismo mensaje si el usuario no existe, la contraseña es incorrecta
            # o la cuenta está inactiva: no se revela cuál de los casos ocurrió.
            return Response(
                {'detail': 'Credenciales inválidas.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response(datos_sesion(user, token))


class RegistroView(APIView):
    # Registro público: cualquiera puede crear su cuenta de organizador.
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegistroSerializer,
        responses={
            201: LoginRespuestaSerializer,
            400: OpenApiResponse(
                description='Datos inválidos, contraseña débil o usuario en uso.'
            ),
        },
    )
    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # La cuenta queda con la sesión iniciada, igual que tras el login.
        token = Token.objects.create(user=user)
        return Response(datos_sesion(user, token), status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        # Borra el token: deja de servir aunque alguien lo haya copiado.
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer

    def get_queryset(self):
        # Cada organizador solo ve y modifica sus eventos (US-11); los de otro
        # responden 404, como si no existieran.
        if getattr(self, 'swagger_fake_view', False):  # generación del esquema OpenAPI
            return Evento.objects.none()
        return Evento.objects.filter(organizador=self.request.user)

    def perform_create(self, serializer):
        serializer.save(organizador=self.request.user)

    @extend_schema(
        request=EventoSerializer,
        responses={
            201: EventoSerializer,
            400: OpenApiResponse(
                description='Error de validación de los datos del evento.'
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'subtareas':
            return SubtareaSerializer
        return EventoSerializer

    @extend_schema(
        request=SubtareaSerializer,
        responses={
            201: SubtareaSerializer,
            400: OpenApiResponse(
                description='Error de validación de los datos de la subtarea.'
            ),
        },
    )
    @action(detail=True, methods=['get', 'post'], url_path='subtareas')
    def subtareas(self, request, pk=None):
        evento = self.get_object()

        if request.method == 'GET':
            subtareas = Subtarea.objects.filter(evento=evento)
            serializer = SubtareaSerializer(subtareas, many=True)
            return Response(serializer.data)

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(evento=evento)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class SubtareaViewSet(viewsets.ModelViewSet):
    queryset = Subtarea.objects.all()
    serializer_class = SubtareaSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # generación del esquema OpenAPI
            return Subtarea.objects.none()
        return Subtarea.objects.filter(evento__organizador=self.request.user)

    def get_serializer_class(self):
        if self.action == 'reprogramar':
            return ReprogramarSubtareaSerializer
        return SubtareaSerializer

    @extend_schema(
        request=ReprogramarSubtareaSerializer,
        responses={
            200: SubtareaHoySerializer,
            400: OpenApiResponse(
                description='No se pudo reprogramar: la fecha objetivo no es válida.'
            ),
            404: OpenApiResponse(
                description='La gestión no existe o es de otro organizador.'
            ),
        },
    )
    @action(detail=True, methods=['patch'], url_path='reprogramar')
    def reprogramar(self, request, pk=None):
        # US-06: cambia solo la fecha objetivo. Devuelve la gestión con la misma
        # forma que en /hoy para que el frontend la mueva a su nuevo grupo.
        subtarea = self.get_object()
        serializer = self.get_serializer(subtarea, data=request.data)

        if not serializer.is_valid():
            return Response(
                {'detail': 'No se pudo reprogramar.', **serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()
        return Response(SubtareaHoySerializer(subtarea).data)

    @extend_schema(
        parameters=[HoyFiltrosSerializer],
        responses={
            200: HoyRespuestaSerializer,
            400: OpenApiResponse(description='Algún filtro no es válido.'),
        },
    )
    @action(detail=False, methods=['get'], url_path='hoy')
    def hoy(self, request):
        # Vista "Hoy" (US-04): vencidas, para hoy y próximas según el plazo
        # respecto a hoy. Dentro de cada grupo, plazo más cercano primero y, si
        # empatan, la de menos horas estimadas. Filtros opcionales (US-05).
        filtros = HoyFiltrosSerializer(data=request.query_params, context={'request': request})
        filtros.is_valid(raise_exception=True)
        evento = filtros.validated_data.get('evento')
        estado = filtros.validated_data.get('estado')
        dias = filtros.validated_data.get('dias')

        hoy = timezone.localdate()
        subtareas = (
            self.get_queryset()
            .select_related('evento')
            .order_by('plazo', 'horas_estimadas', 'nombre')
        )
        if evento is not None:
            subtareas = subtareas.filter(evento=evento)
        if estado is not None:
            condicion = {'vencidas': 'plazo__lt', 'hoy': 'plazo', 'proximas': 'plazo__gt'}[estado]
            subtareas = subtareas.filter(**{condicion: hoy})
        if dias is not None:
            # Vencidas y de hoy siempre caen dentro del rango: solo recorta las próximas.
            subtareas = subtareas.filter(plazo__lte=hoy + timedelta(days=dias))

        grupos = {'vencidas': [], 'hoy': [], 'proximas': []}
        for subtarea in subtareas:
            if subtarea.plazo < hoy:
                grupos['vencidas'].append(subtarea)
            elif subtarea.plazo == hoy:
                grupos['hoy'].append(subtarea)
            else:
                grupos['proximas'].append(subtarea)

        return Response(HoyRespuestaSerializer({'fecha': hoy, **grupos}).data)