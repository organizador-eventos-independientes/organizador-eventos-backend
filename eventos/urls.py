from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventoViewSet, LoginView, LogoutView, SubtareaViewSet

router = DefaultRouter()
router.register(r'eventos', EventoViewSet)
router.register(r'subtareas', SubtareaViewSet)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('', include(router.urls)),
]