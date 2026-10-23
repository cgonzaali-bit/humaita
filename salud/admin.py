
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Enfermedad, Alergia, Lesion, CertificadoMedico, ContactoEmergencia
)


@admin.register(Enfermedad)
class EnfermedadAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'nombre', 'gravedad_badge', 'activa', 'fecha_registro']
    list_filter = ['gravedad', 'activa']
    search_fields = ['alumno__nombre', 'alumno__apellido', 'nombre']
    autocomplete_fields = ['alumno']

    @admin.display(description='Gravedad')
    def gravedad_badge(self, obj):
        colores = {'LEVE': '#6b7280', 'MODERADA': '#f59e0b', 'GRAVE': '#dc2626'}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;">{}</span>',
            colores.get(obj.gravedad, '#999'), obj.get_gravedad_display()
        )


@admin.register(Alergia)
class AlergiaAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'descripcion', 'tipo', 'severidad_badge',
                    'requiere_epipen', 'activa']
    list_filter = ['tipo', 'severidad', 'requiere_epipen', 'activa']
    search_fields = ['alumno__nombre', 'alumno__apellido', 'descripcion']
    autocomplete_fields = ['alumno']

    @admin.display(description='Severidad')
    def severidad_badge(self, obj):
        colores = {'LEVE': '#6b7280', 'MODERADA': '#f59e0b', 'GRAVE': '#dc2626'}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;">{}</span>',
            colores.get(obj.severidad, '#999'), obj.get_severidad_display()
        )


@admin.register(Lesion)
class LesionAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'zona_cuerpo', 'estado', 'fecha_lesion',
                    'dias_desde_lesion']
    list_filter = ['estado', 'zona_cuerpo']
    search_fields = ['alumno__nombre', 'alumno__apellido', 'descripcion']
    date_hierarchy = 'fecha_lesion'
    autocomplete_fields = ['alumno']


@admin.register(CertificadoMedico)
class CertificadoMedicoAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'fecha_emision', 'fecha_vencimiento',
                    'estado_alerta_badge', 'apto_para_competir']
    list_filter = ['apto_para_competir']
    search_fields = ['alumno__nombre', 'alumno__apellido']
    autocomplete_fields = ['alumno']
    date_hierarchy = 'fecha_vencimiento'

    @admin.display(description='Estado')
    def estado_alerta_badge(self, obj):
        colores = {
            'VENCIDO': '#dc2626', 'CRITICO': '#f59e0b',
            'PROXIMO': '#eab308', 'OK': '#10b981',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;">{}</span>',
            colores.get(obj.estado_alerta, '#999'), obj.estado_alerta
        )


@admin.register(ContactoEmergencia)
class ContactoEmergenciaAdmin(admin.ModelAdmin):
    list_display = ['alumno', 'nombre', 'parentesco', 'telefono', 'es_tutor_legal']
    search_fields = ['alumno__nombre', 'alumno__apellido', 'nombre', 'telefono']
    list_filter = ['parentesco', 'es_tutor_legal']
    autocomplete_fields = ['alumno']
