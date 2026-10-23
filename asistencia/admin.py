from django.contrib import admin
from .models import Clase, Asistencia


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'get_dia_semana_display', 'hora_inicio',
                    'hora_fin', 'categoria', 'instructor', 'activo']
    list_filter = ['dia_semana', 'categoria', 'activo']
    search_fields = ['nombre']


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'clase', 'fecha', 'presente', 'registrado_por']
    list_filter = ['presente', 'fecha', 'clase']
    search_fields = ['alumno__nombre', 'alumno__apellido']
    date_hierarchy = 'fecha'
    autocomplete_fields = ['alumno']