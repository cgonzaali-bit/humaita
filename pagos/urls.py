from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.payments_dashboard, name='payments_dashboard'),

    # Planes
    path('planes/', views.plan_list, name='plan_list'),
    path('planes/nuevo/', views.plan_create, name='plan_create'),
    path('planes/<int:pk>/editar/', views.plan_update, name='plan_update'),
    path('planes/<int:pk>/eliminar/', views.plan_delete, name='plan_delete'),

    # Pagos
    path('pagos/', views.pago_list, name='pago_list'),
    path('pagos/nuevo/', views.pago_create, name='pago_create'),
    path('pagos/<int:pk>/', views.pago_detail, name='pago_detail'),
    path('pagos/<int:pk>/editar/', views.pago_update, name='pago_update'),
    path('pagos/<int:pk>/recibo/', views.pago_recibo_pdf, name='pago_recibo_pdf'),
    path('pagos/<int:pk>/marcar-pagado/', views.pago_marcar_pagado, name='pago_marcar_pagado'),
    path('pagos/<int:pk>/eliminar/', views.pago_delete, name='pago_delete'),

    # Generación masiva
    path('generar-mensualidades/', views.generar_mensualidades, name='generar_mensualidades'),

    # Morosos
    path('morosos/', views.morosos, name='morosos'),

    # Reportes
    path('reporte/', views.reporte_recaudacion, name='reporte_recaudacion'),
    path('reporte/pdf/', views.reporte_recaudacion_pdf, name='reporte_recaudacion_pdf'),

    # Promociones
    path('promociones/', views.promocion_list, name='promocion_list'),
    path('promociones/nueva/', views.promocion_create, name='promocion_create'),
    path('promociones/<int:pk>/editar/', views.promocion_update, name='promocion_update'),
    path('api/plan/<int:pk>/', views.api_plan_detalle, name='api_plan_detalle'),
]