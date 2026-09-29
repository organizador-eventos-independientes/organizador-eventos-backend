from django.contrib.auth import authenticate
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
    LoginRespuestaSerializer,
    LoginSerializer,
    SubtareaSerializer,
)


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
        return Response({
            'token': token.key,
            'usuario': {
                'id': user.id,
                'username': user.username,
                'nombre': user.get_full_name() or user.username,
            },
        })


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