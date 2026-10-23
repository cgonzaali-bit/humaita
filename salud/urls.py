from django.urls import path
from . import views

urlpatterns = [
    # Panel central
    path('', views.health_dashboard, name='health_dashboard'),

    # Enfermedades
    path('alumno/<int:alumno_pk>/enfermedad/nueva/',
         views.enfermedad_create, name='enfermedad_create'),
    path('enfermedad/<int:pk>/editar/',
         views.enfermedad_update, name='enfermedad_update'),
    path('enfermedad/<int:pk>/eliminar/',
         views.enfermedad_delete, name='enfermedad_delete'),

    # Alergias
    path('alumno/<int:alumno_pk>/alergia/nueva/',
         views.alergia_create, name='alergia_create'),
    path('alergia/<int:pk>/editar/',
         views.alergia_update, name='alergia_update'),
    path('alergia/<int:pk>/eliminar/',
         views.alergia_delete, name='alergia_delete'),

    # Lesiones
    path('alumno/<int:alumno_pk>/lesion/nueva/',
         views.lesion_create, name='lesion_create'),
    path('lesion/<int:pk>/editar/',
         views.lesion_update, name='lesion_update'),
    path('lesion/<int:pk>/eliminar/',
         views.lesion_delete, name='lesion_delete'),

    # Certificado médico
    path('alumno/<int:alumno_pk>/certificado/',
         views.certificado_create_or_update, name='certificado_form'),
    path('certificado/<int:pk>/eliminar/',
         views.certificado_delete, name='certificado_delete'),

    # Contacto de emergencia
    path('alumno/<int:alumno_pk>/contacto/',
         views.contacto_create_or_update, name='contacto_form'),
]