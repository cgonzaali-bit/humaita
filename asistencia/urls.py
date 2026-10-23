from django.urls import path
from . import views

urlpatterns = [
    # Calendario
    path('', views.calendario, name='calendario'),

    # Clases
    path('clases/', views.clase_list, name='clase_list'),
    path('clases/nueva/', views.clase_create, name='clase_create'),
    path('clases/<int:pk>/editar/', views.clase_update, name='clase_update'),
    path('clases/<int:pk>/eliminar/', views.clase_delete, name='clase_delete'),

    # Check-in rápido
    path('check-in/', views.check_in, name='check_in'),
    path('check-in/buscar/', views.check_in_buscar, name='check_in_buscar'),
    path('marcar/<int:alumno_pk>/', views.marcar_presente, name='marcar_presente'),

    # Asistencia manual
    path('manual/', views.asistencia_manual, name='asistencia_manual'),

    # Historial y estadísticas
    path('historial/', views.asistencia_historial, name='asistencia_historial'),
    path('estadisticas/<int:alumno_pk>/', views.estadisticas_alumno, name='estadisticas_alumno'),
]