
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import date, timedelta

from usuarios.decorators import admin_required, instructor_required
from usuarios.models import AuditLog
from alumnos.models import Student
from .models import Clase, Asistencia
from .forms import ClaseForm, CheckInForm


def _log(user, accion, modelo, obj_id, descripcion, request):
    AuditLog.objects.create(
        usuario=user, accion=accion, modelo_afectado=modelo,
        objeto_id=str(obj_id), descripcion=descripcion,
        ip_address=request.META.get('REMOTE_ADDR'),
    )


# ============================================================
# CALENDARIO SEMANAL
# ============================================================
@instructor_required
def calendario(request):
    """Vista semanal de las clases."""
    clases_por_dia = {}
    for dia_num, dia_label in Clase.DiaSemana.choices:
        clases_por_dia[dia_label] = Clase.objects.filter(activo=True) \
            .filter(dia_semana=dia_num) \
            .select_related('instructor') \
            .order_by('hora_inicio')

    return render(request, 'asistencia/calendario.html', {
        'clases_por_dia': clases_por_dia,
    })


# ============================================================
# CRUD DE CLASES
# ============================================================
@admin_required
def clase_list(request):
    clases = Clase.objects.all().annotate(
        total_asistencias=Count('asistencias')
    ).order_by('dia_semana', 'hora_inicio')
    return render(request, 'asistencia/clase_list.html', {'clases': clases})


@admin_required
def clase_create(request):
    form = ClaseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Clase creada.')
        return redirect('clase_list')
    return render(request, 'asistencia/clase_form.html', {
        'form': form, 'titulo': 'Nueva clase',
    })


@admin_required
def clase_update(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    form = ClaseForm(request.POST or None, instance=clase)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Clase actualizada.')
        return redirect('clase_list')
    return render(request, 'asistencia/clase_form.html', {
        'form': form, 'titulo': f'Editar: {clase.nombre}', 'clase': clase,
    })


@admin_required
@require_http_methods(['POST'])
def clase_delete(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    nombre = clase.nombre
    clase.delete()
    messages.success(request, f'Clase "{nombre}" eliminada.')
    return redirect('clase_list')


# ============================================================
# CHECK-IN RÁPIDO
# ============================================================
@instructor_required
def check_in(request):
    """
    Panel de check-in rápido: se elige clase + fecha,
    luego se busca alumno por nombre/RUT y se marca presente con un click.
    """
    # Clase por defecto: la primera activa
    clases = Clase.objects.filter(activo=True).order_by('dia_semana', 'hora_inicio')
    clase_id = request.GET.get('clase_id')
    clase = None

    if clase_id:
        clase = get_object_or_404(Clase, pk=clase_id)
    elif clases.exists():
        # Sugerir clase según el día de hoy
        hoy_dia = timezone.now().weekday()
        sugerida = clases.filter(dia_semana=hoy_dia).first()
        clase = sugerida or clases.first()

    fecha_str = request.GET.get('fecha', timezone.now().date().isoformat())
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        fecha = timezone.now().date()

    # Asistencias ya registradas en esa clase/fecha
    asistencias = []
    if clase:
        asistencias = Asistencia.objects.filter(
            clase=clase, fecha=fecha
        ).select_related('alumno').order_by('-hora_registro')

    return render(request, 'asistencia/check_in.html', {
        'clases': clases,
        'clase': clase,
        'fecha': fecha,
        'asistencias': asistencias,
        'form': CheckInForm(),
    })


@instructor_required
def check_in_buscar(request):
    """
    Endpoint HTMX: busca alumnos por nombre/RUT y muestra botón de check-in.
    Incluye indicador si ya están presentes en la clase/fecha.
    """
    q = request.GET.get('q', '').strip()
    clase_id = request.GET.get('clase_id')
    fecha_str = request.GET.get('fecha', timezone.now().date().isoformat())

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        fecha = timezone.now().date()

    clase = None
    if clase_id:
        try:
            clase = Clase.objects.get(pk=clase_id)
        except Clase.DoesNotExist:
            pass

    if len(q) < 2:
        return render(request, 'asistencia/partials/_busqueda_vacia.html')

    alumnos = Student.objects.filter(
        Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(dni__icontains=q),
        estado='ACTIVO',
    ).order_by('apellido', 'nombre')[:8]

    # Marcar cuáles ya están presentes
    presentes_ids = set()
    if clase:
        presentes_ids = set(
            Asistencia.objects.filter(
                clase=clase, fecha=fecha, presente=True
            ).values_list('alumno_id', flat=True)
        )

    return render(request, 'asistencia/partials/_resultados_busqueda.html', {
        'alumnos': alumnos,
        'clase': clase,
        'fecha': fecha,
        'presentes_ids': presentes_ids,
    })


@instructor_required
@require_http_methods(['POST'])
def marcar_presente(request, alumno_pk):
    """Marca (o desmarca) la asistencia de un alumno en una clase/fecha."""
    alumno = get_object_or_404(Student, pk=alumno_pk)
    clase_id = request.POST.get('clase_id')
    fecha_str = request.POST.get('fecha')

    if not clase_id or not fecha_str:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)

    clase = get_object_or_404(Clase, pk=clase_id)
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'error': 'Fecha inválida'}, status=400)

    # Toggle: si existe, eliminar; si no, crear
    existente = Asistencia.objects.filter(
        alumno=alumno, clase=clase, fecha=fecha
    ).first()

    if existente:
        existente.delete()
        accion = 'eliminada'
        presente = False
    else:
        Asistencia.objects.create(
            alumno=alumno, clase=clase, fecha=fecha,
            presente=True, registrado_por=request.user,
        )
        accion = 'registrada'
        presente = True

        _log(request.user, 'CREAR', 'Asistencia', alumno.pk,
             f'Check-in: {alumno} en {clase.nombre} ({fecha})', request)

    return JsonResponse({
        'ok': True,
        'presente': presente,
        'accion': accion,
        'alumno_nombre': f'{alumno.nombre} {alumno.apellido}',
    })


# ============================================================
# ASISTENCIA MANUAL (GRUPAL)
# ============================================================
@instructor_required
def asistencia_manual(request):
    """
    Vista para marcar asistencia de toda una clase del día,
    con checkboxes por alumno.
    """
    clase_id = request.GET.get('clase_id')
    fecha_str = request.GET.get('fecha', timezone.now().date().isoformat())

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        fecha = timezone.now().date()

    clase = None
    if clase_id:
        clase = get_object_or_404(Clase, pk=clase_id)

    alumnos = []
    asistencias_dict = {}

    if clase:
        # Filtrar alumnos por categoría de la clase
        alumno_qs = Student.objects.filter(estado='ACTIVO')
        if clase.categoria == 'INFANTIL':
            alumno_qs = alumno_qs.filter(categoria='INFANTIL')
        elif clase.categoria == 'JUVENIL':
            alumno_qs = alumno_qs.filter(categoria='JUVENIL')
        elif clase.categoria == 'ADULTO':
            alumno_qs = alumno_qs.filter(categoria__in=['ADULTO', 'MASTER'])
        elif clase.categoria == 'PRINCIPIANTES':
            alumno_qs = alumno_qs.filter(cinturon_actual='BLANCO')
        elif clase.categoria == 'COMPETIDORES':
            # Simplificación: alumnos que han competido
            alumno_qs = alumno_qs.filter(
                inscripciones_eventos__evento__tipo='COMPETENCIA'
            ).distinct()

        alumnos = alumno_qs.order_by('apellido', 'nombre')

        # Diccionario de asistencias existentes
        asistencias_dict = {
            a.alumno_id: a
            for a in Asistencia.objects.filter(clase=clase, fecha=fecha)
        }

    # Procesar POST
    if request.method == 'POST' and clase:
        presentes_ids = set(
            int(x) for x in request.POST.getlist('presentes')
        )

        creados = 0
        eliminados = 0
        for alumno in alumnos:
            existe = asistencias_dict.get(alumno.pk)

            if alumno.pk in presentes_ids and not existe:
                Asistencia.objects.create(
                    alumno=alumno, clase=clase, fecha=fecha,
                    presente=True, registrado_por=request.user,
                )
                creados += 1
            elif alumno.pk not in presentes_ids and existe:
                existe.delete()
                eliminados += 1

        messages.success(
            request,
            f'Asistencia guardada: {creados} nuevos, {eliminados} eliminados.'
        )
        return redirect(f'/asistencia/manual/?clase_id={clase.pk}&fecha={fecha}')

    return render(request, 'asistencia/asistencia_manual.html', {
        'clases': Clase.objects.filter(activo=True).order_by('dia_semana', 'hora_inicio'),
        'clase': clase,
        'fecha': fecha,
        'alumnos': alumnos,
        'asistencias_dict': asistencias_dict,
    })


# ============================================================
# HISTORIAL Y ESTADÍSTICAS
# ============================================================
@instructor_required
def asistencia_historial(request):
    """Historial de asistencias con filtros."""
    qs = Asistencia.objects.select_related('alumno', 'clase') \
        .order_by('-fecha', 'clase__hora_inicio')

    # Filtros
    q = request.GET.get('q', '').strip()
    clase_id = request.GET.get('clase_id', '')
    desde = request.GET.get('desde', '')
    hasta = request.GET.get('hasta', '')

    if q:
        qs = qs.filter(
            Q(alumno__nombre__icontains=q) | Q(alumno__apellido__icontains=q)
        )
    if clase_id:
        qs = qs.filter(clase_id=clase_id)
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'asistencia/asistencia_historial.html', {
        'page_obj': page_obj,
        'clases': Clase.objects.filter(activo=True),
        'q': q, 'clase_id': clase_id, 'desde': desde, 'hasta': hasta,
    })


@instructor_required
def estadisticas_alumno(request, alumno_pk):
    """Estadísticas de asistencia de un alumno."""
    alumno = get_object_or_404(Student, pk=alumno_pk)

    # Total de asistencias
    total = Asistencia.objects.del_alumno(alumno).presentes().count()

    # Últimos 3 meses
    hoy = timezone.now().date()
    hace_3_meses = hoy - timedelta(days=90)
    recientes = Asistencia.objects.del_alumno(alumno).presentes() \
        .filter(fecha__gte=hace_3_meses).count()

    # Por clase
    por_clase = Asistencia.objects.del_alumno(alumno) \
        .filter(presente=True) \
        .values('clase__nombre') \
        .annotate(total=Count('id')) \
        .order_by('-total')

    # Últimas asistencias
    ultimas = Asistencia.objects.del_alumno(alumno) \
        .select_related('clase') \
        .order_by('-fecha')[:20]

    return render(request, 'asistencia/estadisticas_alumno.html', {
        'alumno': alumno,
        'total': total,
        'recientes': recientes,
        'por_clase': por_clase,
        'ultimas': ultimas,
    })