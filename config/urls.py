
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reportes.urls')),         # ← Dashboard global en /
    path('auth', include('usuarios.urls')),   # ← Login, staff (cambiado de /)
    path('usuarios/', include('django.contrib.auth.urls')),
    path('alumnos/', include('alumnos.urls')),
    path('salud/', include('salud.urls')),
    path('pagos/', include('pagos.urls')),
    path('eventos/', include('eventos.urls')),
    path('asistencia/', include('asistencia.urls')),
    
    

  
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


