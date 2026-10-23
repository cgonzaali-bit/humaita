from django.contrib import admin
from django.utils.html import format_html
from .models import PlanPago, Pago, Promocion


@admin.register(PlanPago)
class PlanPagoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'monto', 'tipo_alumno', 'get_frecuencia_display',
                    'es_familiar', 'activo']
    list_filter = ['tipo_alumno', 'frecuencia', 'es_familiar', 'activo']
    search_fields = ['nombre']


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['numero_recibo', 'alumno', 'periodo', 'monto_final',
                    'estado_badge', 'metodo_pago', 'fecha_pago']
    list_filter = ['estado', 'metodo_pago', 'anio', 'mes']
    search_fields = ['alumno__nombre', 'alumno__apellido', 'numero_recibo']
    date_hierarchy = 'fecha_pago'
    autocomplete_fields = ['alumno']
    readonly_fields = ['monto_final', 'numero_recibo', 'creado_en', 'actualizado_en']

    @admin.display(description='Período')
    def periodo(self, obj):
        return obj.periodo_display

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        colores = {
            'PAGADO': '#10b981', 'PENDIENTE': '#f59e0b',
            'ATRASADO': '#dc2626', 'EXIMIDO': '#6b7280', 'BECA': '#3b82f6',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;">{}</span>',
            colores.get(obj.estado, '#999'), obj.get_estado_display()
        )


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'valor', 'fecha_inicio', 'fecha_fin', 'activa']
    list_filter = ['tipo', 'activa']