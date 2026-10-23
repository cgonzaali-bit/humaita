
from django.contrib import admin
from django.utils.html import format_html
from .models import Student, BeltHistory


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        'foto_thumb', 'apellido', 'nombre', 'rut',
        'cinturon_badge', 'categoria', 'estado_badge', 'fecha_inicio',
    ]
    list_filter = ['estado', 'cinturon_actual', 'categoria']
    search_fields = ['nombre', 'apellido', 'rut', 'email']
    readonly_fields = ['fecha_inicio', 'foto_preview']
    list_per_page = 30

    fieldsets = (
        ('Datos personales', {
            'fields': ('nombre', 'apellido', 'fecha_nacimiento', 'rut',
                       'telefono', 'email', 'direccion')
        }),
        ('Foto', {
            'fields': ('foto_perfil', 'foto_preview')
        }),
        ('Información deportiva', {
            'fields': ('cinturon_actual', 'grados_cinturon', 'categoria',
                       'estado', 'fecha_inicio')
        }),
        ('Tutor (obligatorio si es menor)', {
            'fields': ('tutor_nombre', 'tutor_telefono', 'tutor_parentesco')
        }),
        ('Notas', {
            'fields': ('notas',)
        }),
    )

    @admin.display(description='Foto')
    def foto_thumb(self, obj):
        if obj.foto_perfil:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;'
                'border-radius:50%;object-fit:cover;" />',
                obj.foto_perfil.url
            )
        return '—'

    @admin.display(description='Vista previa')
    def foto_preview(self, obj):
        if obj.foto_perfil:
            return format_html(
                '<img src="{}" style="max-width:200px;border-radius:8px;" />',
                obj.foto_perfil.url
            )
        return 'Sin foto'

    @admin.display(description='Cinturón')
    def cinturon_badge(self, obj):
        colores = {
            'BLANCO': '#f3f4f6',
            'AZUL': '#3b82f6',
            'MORADO': '#8b5cf6',
            'MARRON': '#78350f',
            'NEGRO': '#000000',
        }
        texto = {
            'BLANCO': '#111827', 'AZUL': '#fff', 'MORADO': '#fff',
            'MARRON': '#fff', 'NEGRO': '#fff',
        }
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:6px;font-size:11px;font-weight:600;">{}</span>',
            colores.get(obj.cinturon_actual, '#eee'),
            texto.get(obj.cinturon_actual, '#000'),
            f'{obj.get_cinturon_actual_display()} ({obj.grados_cinturon})'
        )

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        colores = {
            'ACTIVO': '#10b981', 'INACTIVO': '#6b7280',
            'CONGELADO': '#f59e0b',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;">{}</span>',
            colores.get(obj.estado, '#999'),
            obj.get_estado_display(),
        )


@admin.register(BeltHistory)
class BeltHistoryAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'cinturon_anterior', 'cinturon_nuevo',
                    'grados', 'fecha_promocion', 'instructor']
    list_filter = ['cinturon_nuevo', 'fecha_promocion']
    search_fields = ['alumno__nombre', 'alumno__apellido']
    date_hierarchy = 'fecha_promocion'