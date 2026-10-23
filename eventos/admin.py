from django.contrib import admin
from django.utils.html import format_html
from .models import Evento, InscripcionEvento, FotoEvento


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'fecha', 'estado_badge',
                    'inscritos', 'total_recaudado_display']
    list_filter = ['tipo', 'estado', 'activo']
    search_fields = ['nombre', 'lugar']
    date_hierarchy = 'fecha'

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        colores = {
            'BORRADOR': '#6b7280', 'ABIERTO': '#10b981',
            'CERRADO': '#f59e0b', 'EN_CURSO': '#3b82f6',
            'FINALIZADO': '#8b5cf6', 'CANCELADO': '#dc2626',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;">{}</span>',
            colores.get(obj.estado, '#999'), obj.get_estado_display()
        )

    @admin.display(description='Inscritos')
    def inscritos(self, obj):
        return obj.total_inscritos

    @admin.display(description='Recaudado')
    def total_recaudado_display(self, obj):
        return f'${obj.total_recaudado:,.0f}'


@admin.register(InscripcionEvento)
class InscripcionEventoAdmin(admin.ModelAdmin):
    list_display = ['evento', 'alumno', 'estado_pago', 'monto_pagado',
                    'resultado', 'posicion']
    list_filter = ['estado_pago', 'resultado']
    search_fields = ['alumno__nombre', 'alumno__apellido', 'evento__nombre']
    autocomplete_fields = ['alumno']


@admin.register(FotoEvento)
class FotoEventoAdmin(admin.ModelAdmin):
    list_display = ['evento', 'titulo', 'subida_en']
    list_filter = ['evento']