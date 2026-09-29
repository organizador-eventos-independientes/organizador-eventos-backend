from django.contrib import admin

from .models import Evento, Subtarea


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    # Desde aquí se asigna organizador a los eventos creados antes del login.
    list_display = ('titulo', 'fecha', 'organizador')
    list_filter = ('organizador',)


@admin.register(Subtarea)
class SubtareaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'evento', 'plazo')
