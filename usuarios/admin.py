from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'username', 'get_full_name', 'email', 'role_badge',
        'cinturon_display', 'nivel_display', 'activo', 'ultimo_acceso',
    ]
    list_filter = ['role', 'cinturon_actual', 'activo', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_per_page = 30

    fieldsets = BaseUserAdmin.fieldsets + (
        ('ArmyLock - Rol y acceso', {
            'fields': ('role', 'activo', 'telefono'),
        }),
        ('ArmyLock - Cinturón', {
            'fields': ('cinturon_actual', 'grados_cinturon'),
        }),
        ('ArmyLock - Perfil de instructor', {
            'fields': (
                'fecha_inicio_ensenanza', 'profesor_mentor',
                'biografia', 'especialidades', 'certificaciones',
                'horario_disponible',
            ),
            'classes': ('collapse',),
        }),
        ('ArmyLock - Foto', {
            'fields': ('foto_perfil', 'foto_preview'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('ArmyLock', {
            'fields': ('role', 'email', 'first_name', 'last_name',
                       'cinturon_actual', 'grados_cinturon'),
        }),
    )

    readonly_fields = ['ultimo_acceso', 'foto_preview']

    @admin.display(description='Rol')
    def role_badge(self, obj):
        colores = {
            'SUPER_ADMIN': '#111827', 'ADMIN': '#3b82f6',
            'INSTRUCTOR': '#8b5cf6', 'ALUMNO': '#6b7280',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;">{}</span>',
            colores.get(obj.role, '#999'), obj.get_role_display(),
        )

    @admin.display(description='Cinturón')
    def cinturon_display(self, obj):
        colores = {
            'BLANCO': '#f3f4f6', 'AZUL': '#3b82f6', 'MORADO': '#8b5cf6',
            'MARRON': '#78350f', 'NEGRO': '#000000',
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
            f'{obj.get_cinturon_actual_display()} ({obj.grados_cinturon}º)',
        )

    @admin.display(description='Nivel')
    def nivel_display(self, obj):
        return obj.nivel_instructor_display or '—'

    @admin.display(description='Vista previa')
    def foto_preview(self, obj):
        if obj.foto_perfil:
            return format_html(
                '<img src="{}" style="max-width:150px;border-radius:8px;" />',
                obj.foto_perfil.url,
            )
        return 'Sin foto'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'usuario', 'accion', 'modelo_afectado', 'descripcion']
    list_filter = ['accion', 'timestamp']
    search_fields = ['descripcion', 'usuario__username']
    readonly_fields = ['timestamp', 'usuario', 'accion', 'modelo_afectado',
                       'objeto_id', 'descripcion', 'ip_address']