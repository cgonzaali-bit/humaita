from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods

from .models import User, AuditLog
from .forms import LoginForm, StaffCreateForm, StaffUpdateForm
from .decorators import super_admin_required, admin_required


# ============================================================
# HELPERS
# ============================================================
def _log(user, accion, modelo, obj_id, descripcion, request):
    AuditLog.objects.create(
        usuario=user, accion=accion, modelo_afectado=modelo,
        objeto_id=str(obj_id), descripcion=descripcion,
        ip_address=request.META.get('REMOTE_ADDR'),
    )


# ============================================================
# AUTH
# ============================================================
def login_view(request):
    """Vista de login con auditoría."""
    if request.user.is_authenticated:
        return redirect('dashboard_global')

    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)

        AuditLog.objects.create(
            usuario=user, accion='LOGIN',
            descripcion=f'Inicio de sesión desde {request.META.get("REMOTE_ADDR")}',
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        user.ultimo_acceso = timezone.now()
        user.save(update_fields=['ultimo_acceso'])

        messages.success(
            request, f'Bienvenido, {user.get_full_name() or user.username}'
        )
        return redirect('dashboard_global')

    return render(request, 'usuarios/login.html', {'form': form})



# ============================================================
# DASHBOARD (redirige al global)
# ============================================================
@login_required
def dashboard(request):
    return redirect('dashboard_global')


# ============================================================
# STAFF: LISTADO
# ============================================================
@admin_required
def staff_list(request):
    """
    Listado del staff (admins, instructores, monitores, profesores).
    Filtrable por rol, cinturón y estado.
    """
    qs = User.objects.exclude(role=User.Role.ALUMNO) \
        .select_related('profesor_mentor') \
        .annotate(
            num_clases=Count('clases_impartidas', distinct=True),
        ) \
        .order_by('-role', 'last_name', 'first_name')

    # Filtros
    q = request.GET.get('q', '').strip()
    rol = request.GET.get('rol', '')
    cinturon = request.GET.get('cinturon', '')
    estado = request.GET.get('estado', '')

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(username__icontains=q)
            | Q(email__icontains=q)
        )
    if rol:
        qs = qs.filter(role=rol)
    if cinturon:
        qs = qs.filter(cinturon_actual=cinturon)
    if estado == 'activo':
        qs = qs.filter(activo=True)
    elif estado == 'inactivo':
        qs = qs.filter(activo=False)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # Estadísticas
    total_staff = User.objects.exclude(role=User.Role.ALUMNO).count()
    total_instructores = User.objects.filter(
        role__in=['SUPER_ADMIN', 'ADMIN', 'INSTRUCTOR'],
        cinturon_actual__in=['AZUL', 'MORADO', 'MARRON', 'NEGRO'],
        activo=True,
    ).count()

    # Desglose por nivel
    por_nivel = {
        'MONITOR': User.objects.filter(
            role__in=['INSTRUCTOR', 'ADMIN', 'SUPER_ADMIN'],
            cinturon_actual='AZUL', activo=True,
        ).count(),
        'INSTRUCTOR': User.objects.filter(
            role__in=['INSTRUCTOR', 'ADMIN', 'SUPER_ADMIN'],
            cinturon_actual='MORADO', activo=True,
        ).count(),
        'INSTRUCTOR_AVANZADO': User.objects.filter(
            role__in=['INSTRUCTOR', 'ADMIN', 'SUPER_ADMIN'],
            cinturon_actual='MARRON', activo=True,
        ).count(),
        'PROFESOR': User.objects.filter(
            role__in=['INSTRUCTOR', 'ADMIN', 'SUPER_ADMIN'],
            cinturon_actual='NEGRO', activo=True,
        ).count(),
    }

    context = {
        'page_obj': page_obj,
        'total_staff': total_staff,
        'total_instructores': total_instructores,
        'por_nivel': por_nivel,
        'roles': [
            (r.value, r.label) for r in User.Role
            if r.value != User.Role.ALUMNO
        ],
        'cinturones': User.Cinturon.choices,
        'q': q, 'rol': rol, 'cinturon': cinturon, 'estado': estado,
    }
    return render(request, 'usuarios/staff_list.html', context)


# ============================================================
# STAFF: DETALLE
# ============================================================
@admin_required
def staff_detail(request, pk):
    """Ficha completa del miembro del staff."""
    staff = get_object_or_404(
        User.objects.exclude(role=User.Role.ALUMNO),
        pk=pk,
    )

    # Clases asignadas
    from asistencia.models import Clase
    clases = Clase.objects.filter(instructor=staff, activo=True) \
        .order_by('dia_semana', 'hora_inicio')

    # Alumnos formados (si es mentor)
    alumnos_formados = User.objects.filter(profesor_mentor=staff)

    # Promociones otorgadas
    from alumnos.models import BeltHistory
    promociones_otorgadas = BeltHistory.objects.filter(
        instructor=staff
    ).select_related('alumno').order_by('-fecha_promocion')[:10]

    context = {
        'staff': staff,
        'clases': clases,
        'alumnos_formados': alumnos_formados,
        'promociones_otorgadas': promociones_otorgadas,
    }
    return render(request, 'usuarios/staff_detail.html', context)


# ============================================================
# STAFF: CREAR
# ============================================================
@super_admin_required
def staff_create(request):
    """
    Crear nuevo miembro del staff.
    Solo SUPER_ADMIN puede crear otros admins/instructores.
    """
    form = StaffCreateForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()

        _log(
            request.user, 'CREAR', 'User', user.pk,
            f'Creó {user.get_role_display()} "{user.username}" '
            f'(cinturón {user.get_cinturon_actual_display()})',
            request,
        )

        messages.success(
            request,
            f'{user.get_role_display()} {user.get_full_name()} creado correctamente.'
        )
        return redirect('staff_detail', pk=user.pk)

    return render(request, 'usuarios/staff_form.html', {
        'form': form,
        'titulo': 'Nuevo miembro del staff',
        'accion': 'Crear',
        'es_creacion': True,
    })


# ============================================================
# STAFF: EDITAR
# ============================================================
@admin_required
def staff_update(request, pk):
    """Editar miembro del staff existente."""
    staff = get_object_or_404(
        User.objects.exclude(role=User.Role.ALUMNO),
        pk=pk,
    )

    # Solo SUPER_ADMIN puede editar a otros admins
    if staff.es_admin and not request.user.es_super_admin:
        messages.error(
            request,
            'Solo el SUPER_ADMIN puede editar a otros administradores.'
        )
        return redirect('staff_detail', pk=staff.pk)

    form = StaffUpdateForm(
        request.POST or None,
        request.FILES or None,
        instance=staff,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        _log(
            request.user, 'EDITAR', 'User', staff.pk,
            f'Editó al staff "{staff.username}"',
            request,
        )
        messages.success(request, 'Datos actualizados correctamente.')
        return redirect('staff_detail', pk=staff.pk)

    return render(request, 'usuarios/staff_form.html', {
        'form': form,
        'titulo': f'Editar: {staff.get_full_name() or staff.username}',
        'accion': 'Guardar cambios',
        'staff': staff,
        'es_creacion': False,
    })


# ============================================================
# STAFF: ELIMINAR
# ============================================================
@super_admin_required
@require_http_methods(['POST'])
def staff_delete(request, pk):
    """Eliminar miembro del staff (con validaciones)."""
    staff = get_object_or_404(
        User.objects.exclude(role=User.Role.ALUMNO),
        pk=pk,
    )

    # No eliminarse a sí mismo
    if staff.pk == request.user.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
        return redirect('staff_detail', pk=staff.pk)

    # No eliminar si tiene clases asignadas
    from asistencia.models import Clase
    if Clase.objects.filter(instructor=staff).exists():
        messages.error(
            request,
            f'No se puede eliminar a {staff.get_full_name()}: '
            'tiene clases asignadas. Reasígnalas o desactívalo en su lugar.'
        )
        return redirect('staff_detail', pk=staff.pk)

    nombre = staff.get_full_name() or staff.username
    staff.delete()

    _log(
        request.user, 'ELIMINAR', 'User', pk,
        f'Eliminó al staff "{nombre}"', request,
    )

    messages.success(request, f'Miembro del staff "{nombre}" eliminado.')
    return redirect('staff_list')


# ============================================================
# STAFF: TOGGLE ACTIVO
# ============================================================
@admin_required
@require_http_methods(['POST'])
def staff_toggle_activo(request, pk):
    """Activa o desactiva un miembro del staff."""
    staff = get_object_or_404(
        User.objects.exclude(role=User.Role.ALUMNO),
        pk=pk,
    )

    if staff.pk == request.user.pk:
        messages.error(request, 'No puedes desactivar tu propia cuenta.')
        return redirect('staff_detail', pk=staff.pk)

    staff.activo = not staff.activo
    staff.save(update_fields=['activo'])

    estado = 'activado' if staff.activo else 'desactivado'
    messages.success(request, f'{staff.get_full_name() or staff.username} {estado}.')
    return redirect('staff_detail', pk=staff.pk)


# ============================================================
# STAFF: RESET PASSWORD
# ============================================================
@super_admin_required
@require_http_methods(['POST'])
def staff_reset_password(request, pk):
    """Envía un email de reset de contraseña al miembro del staff."""
    staff = get_object_or_404(
        User.objects.exclude(role=User.Role.ALUMNO),
        pk=pk,
    )

    if not staff.email:
        messages.error(request, 'Este usuario no tiene email registrado.')
        return redirect('staff_detail', pk=staff.pk)

    # Generar token y enviar email (usa el flujo nativo de Django)
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.urls import reverse
    from django.core.mail import send_mail
    from django.conf import settings

    token = default_token_generator.make_token(staff)
    uid = urlsafe_base64_encode(force_bytes(staff.pk))
    reset_url = request.build_absolute_uri(
        reverse('password_reset_confirm', kwargs={
            'uidb64': uid, 'token': token,
        })
    )

    try:
        send_mail(
            subject='Restablecer contraseña - ArmyLock',
            message=(
                f'Hola {staff.get_full_name()},\n\n'
                f'Se ha solicitado restablecer tu contraseña. '
                f'Usa este enlace:\n\n{reset_url}\n\n'
                f'Si no fuiste tú, ignora este correo.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[staff.email],
            fail_silently=False,
        )
        messages.success(
            request,
            f'Se envió un email de restablecimiento a {staff.email}.'
        )
    except Exception as e:
        messages.error(request, f'Error al enviar email: {e}')

    return redirect('staff_detail', pk=staff.pk)




def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(
            usuario=request.user, accion='LOGOUT',
            descripcion='Cierre de sesión',
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        logout(request)
    return redirect('login')


