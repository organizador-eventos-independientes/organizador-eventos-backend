from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConfiguracionView,
    EventoViewSet,
    LoginView,
    LogoutView,
    RegistroView,
    SubtareaViewSet,
)

router = DefaultRouter()
router.register(r'eventos', EventoViewSet)
router.register(r'subtareas', SubtareaViewSet)

urlpatterns = [
    path('auth/registro/', RegistroView.as_view(), name='registro'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('configuracion/', ConfiguracionView.as_view(), name='configuracion'),
    path('', include(router.urls)),
]