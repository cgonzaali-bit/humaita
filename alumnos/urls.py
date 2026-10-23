from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_list, name='student_list'),
    path('buscar/', views.student_search, name='student_search'),
    path('nuevo/', views.student_create, name='student_create'),
    path('<int:pk>/', views.student_detail, name='student_detail'),
    path('<int:pk>/editar/', views.student_update, name='student_update'),
    path('<int:pk>/eliminar/', views.student_delete, name='student_delete'),
    path('<int:pk>/promover/', views.student_promote, name='student_promote'),
]