from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Evento, Subtarea
from .serializers import EventoSerializer, SubtareaSerializer


class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer

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