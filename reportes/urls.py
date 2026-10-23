from django.urls import path
from . import views

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard, name='dashboard_global'),

    # Índice de reportes
    path('reportes/', views.reportes_index, name='reportes_index'),

    # Reporte: Alumnos
    path('reportes/alumnos/', views.reporte_alumnos, name='reporte_alumnos'),
    path('reportes/alumnos/excel/', views.reporte_alumnos_excel, name='reporte_alumnos_excel'),

    # Reporte: Recaudación
    path('reportes/recaudacion/', views.reporte_recaudacion_global, name='reporte_recaudacion_global'),
    path('reportes/recaudacion/excel/', views.reporte_recaudacion_global_excel, name='reporte_recaudacion_global_excel'),

    # Reporte: Asistencia
    path('reportes/asistencia/', views.reporte_asistencia, name='reporte_asistencia'),
    path('reportes/asistencia/excel/', views.reporte_asistencia_excel, name='reporte_asistencia_excel'),

    # Reporte: Aptos para examen
    path('reportes/aptos-examen/', views.reporte_aptos_examen, name='reporte_aptos_examen'),
    path('reportes/aptos-examen/excel/', views.reporte_aptos_examen_excel, name='reporte_aptos_examen_excel'),

    # Búsqueda global
    path('buscar/', views.busqueda_global, name='busqueda_global'),
]