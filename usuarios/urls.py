
from django.urls import path
from . import views
from django.contrib.auth.views import LoginView  # ← AGREGA ESTA LÍNEA


urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    #path('usuarios/login/', LoginView.as_view(template_name='usuarios/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
   

    # Dashboard (redirige al global)
    path('dashboard/', views.dashboard, name='dashboard'),

    # Staff
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/nuevo/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/', views.staff_detail, name='staff_detail'),
    path('staff/<int:pk>/editar/', views.staff_update, name='staff_update'),
    path('staff/<int:pk>/eliminar/', views.staff_delete, name='staff_delete'),
    path('staff/<int:pk>/toggle-activo/', views.staff_toggle_activo, name='staff_toggle_activo'),
    path('staff/<int:pk>/reset-password/', views.staff_reset_password, name='staff_reset_password'),
]