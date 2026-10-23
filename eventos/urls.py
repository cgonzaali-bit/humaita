from django.urls import path
from . import views

urlpatterns = [
    path('', views.evento_list, name='evento_list'),
    path('nuevo/', views.evento_create, name='evento_create'),
    path('<int:pk>/', views.evento_detail, name='evento_detail'),
    path('<int:pk>/editar/', views.evento_update, name='evento_update'),
    path('<int:pk>/eliminar/', views.evento_delete, name='evento_delete'),

    # Inscripciones
    path('<int:evento_pk>/inscribir/', views.inscripcion_create, name='inscripcion_create'),
    path('<int:evento_pk>/inscribir-masivo/', views.inscripcion_masiva, name='inscripcion_masiva'),
    path('inscripcion/<int:pk>/marcar-pagado/', views.inscripcion_marcar_pagado, name='inscripcion_marcar_pagado'),
    path('inscripcion/<int:pk>/eliminar/', views.inscripcion_delete, name='inscripcion_delete'),
    path('inscripcion/<int:pk>/resultado/', views.resultado_update, name='resultado_update'),

    # Fotos
    path('<int:evento_pk>/fotos/subir/', views.foto_upload, name='foto_upload'),
    path('foto/<int:pk>/eliminar/', views.foto_delete, name='foto_delete'),
]