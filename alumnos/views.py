
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from usuarios.decorators import admin_required, instructor_required
from usuarios.models import AuditLog
from .models import Student, BeltHistory
from .forms import StudentForm, StudentFilterForm, BeltPromotionForm


def _filtrar_alumnos(request):
    """Aplica los filtros del formulario a la queryset de alumnos."""
    qs = Student.objects.all().order_by('apellido', 'nombre')

    q = request.GET.get('q', '').strip()
    cinturon = request.GET.get('cinturon', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    estado = request.GET.get('estado', '').strip()

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(apellido__icontains=q) |
            Q(dni__icontains=q)
        )
    if cinturon:
        qs = qs.filter(cinturon_actual=cinturon)
    if categoria:
        qs = qs.filter(categoria=categoria)
    if estado:
        qs = qs.filter(estado=estado)

    return qs


@instructor_required
def student_list(request):
    """Listado completo de alumnos con filtros y paginación."""
    qs = _filtrar_alumnos(request)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Estadísticas del encabezado
    total_activos = Student.objects.filter(estado='ACTIVO').count()
    total_alumnos = Student.objects.count()

    context = {
        'page_obj': page_obj,
        'filter_form': StudentFilterForm(request.GET),
        'total_alumnos': total_alumnos,
        'total_activos': total_activos,
        'filtros_activos': bool(
            request.GET.get('q') or request.GET.get('cinturon')
            or request.GET.get('categoria') or request.GET.get('estado')
        ),
    }
    return render(request, 'alumnos/student_list.html', context)


@instructor_required
def student_search(request):
    """
    Endpoint parcial que retorna SOLO la tabla de resultados.
    Se usa con HTMX para búsqueda en vivo.
    """
    qs = _filtrar_alumnos(request)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'alumnos/partials/_student_table.html', {
        'page_obj': page_obj,
    })


@instructor_required
def student_detail(request, pk):
    """Vista detallada con pestañas: datos, salud, pagos, asistencia, cinturones."""
    alumno = get_object_or_404(Student, pk=pk)

    # Precargamos relaciones para evitar N+1
    alumno_data = {
        'alumno': alumno,
        'enfermedades': alumno.enfermedades.all(),
        'alergias': alumno.alergias.all(),
        'lesiones': alumno.lesiones.all(),
        'historial_cinturones': alumno.historial_cinturones.select_related('instructor'),
        'pagos': alumno.pagos.select_related('plan').order_by('-anio', '-mes')[:12],
        'asistencias': alumno.asistencias.select_related('clase').order_by('-fecha')[:20],
        'inscripciones': alumno.inscripciones_eventos.select_related('evento'),
    }

    # Intentar cargar contacto de emergencia y certificado si existen
    try:
        alumno_data['contacto_emergencia'] = alumno.contacto_emergencia
    except Exception:
        alumno_data['contacto_emergencia'] = None

    try:
        alumno_data['certificado'] = alumno.certificado_medico
    except Exception:
        alumno_data['certificado'] = None

    return render(request, 'alumnos/student_detail.html', alumno_data)


@admin_required
def student_create(request):
    """Crear nuevo alumno."""
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            alumno = form.save()

            AuditLog.objects.create(
                usuario=request.user,
                accion='CREAR',
                modelo_afectado='Student',
                objeto_id=str(alumno.pk),
                descripcion=f'Creó al alumno {alumno.apellido}, {alumno.nombre}',
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            messages.success(
                request,
                f'Alumno {alumno.nombre} {alumno.apellido} registrado correctamente.'
            )
            return redirect('student_detail', pk=alumno.pk)
    else:
        form = StudentForm()

    return render(request, 'alumnos/student_form.html', {
        'form': form,
        'titulo': 'Nuevo Alumno',
        'accion': 'Crear',
    })


@admin_required
def student_update(request, pk):
    """Editar alumno existente."""
    alumno = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=alumno)
        if form.is_valid():
            form.save()

            AuditLog.objects.create(
                usuario=request.user,
                accion='EDITAR',
                modelo_afectado='Student',
                objeto_id=str(alumno.pk),
                descripcion=f'Editó al alumno {alumno.apellido}, {alumno.nombre}',
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            messages.success(request, 'Datos actualizados correctamente.')
            return redirect('student_detail', pk=alumno.pk)
    else:
        form = StudentForm(instance=alumno)

    return render(request, 'alumnos/student_form.html', {
        'form': form,
        'titulo': f'Editar: {alumno.nombre} {alumno.apellido}',
        'accion': 'Guardar cambios',
        'alumno': alumno,
    })


@admin_required
@require_http_methods(['POST'])
def student_delete(request, pk):
    """Eliminar alumno (soft-check primero)."""
    alumno = get_object_or_404(Student, pk=pk)
    nombre_completo = f'{alumno.nombre} {alumno.apellido}'

    # Verificar si tiene pagos registrados
    if alumno.pagos.exists():
        messages.error(
            request,
            f'No se puede eliminar a {nombre_completo}: tiene pagos registrados. '
            'Considera cambiar su estado a "Inactivo" en lugar de eliminarlo.'
        )
        return redirect('student_detail', pk=pk)

    alumno.delete()

    AuditLog.objects.create(
        usuario=request.user,
        accion='ELIMINAR',
        modelo_afectado='Student',
        objeto_id=str(pk),
        descripcion=f'Eliminó al alumno {nombre_completo}',
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    messages.success(request, f'Alumno {nombre_completo} eliminado.')
    return redirect('student_list')


@admin_required
def student_promote(request, pk):
    """Registrar una promoción de cinturón."""
    alumno = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        form = BeltPromotionForm(request.POST, alumno=alumno)
        if form.is_valid():
            promocion = form.save(commit=False)
            promocion.alumno = alumno
            promocion.cinturon_anterior = alumno.cinturon_actual
            promocion.instructor = request.user
            promocion.save()

            # Actualizar el cinturón actual del alumno
            alumno.cinturon_actual = promocion.cinturon_nuevo
            alumno.grados_cinturon = promocion.grados
            alumno.save(update_fields=['cinturon_actual', 'grados_cinturon'])

            AuditLog.objects.create(
                usuario=request.user,
                accion='EDITAR',
                modelo_afectado='BeltHistory',
                objeto_id=str(promocion.pk),
                descripcion=(
                    f'Promoción de cinturón: {alumno.apellido}, {alumno.nombre} → '
                    f'{promocion.get_cinturon_nuevo_display()} ({promocion.grados} grados)'
                ),
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            messages.success(
                request,
                f'¡Promoción registrada! {alumno.nombre} ahora es '
                f'{promocion.get_cinturon_nuevo_display()}.'
            )
            return redirect('student_detail', pk=alumno.pk)
    else:
        form = BeltPromotionForm(alumno=alumno)

    return render(request, 'alumnos/student_promote.html', {
        'form': form,
        'alumno': alumno,
    })
