from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventoViewSet, SubtareaViewSet

router = DefaultRouter()
router.register(r'eventos', EventoViewSet)
router.register(r'subtareas', SubtareaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]