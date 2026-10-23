
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from usuarios.decorators import admin_required, instructor_required
from usuarios.models import AuditLog
from alumnos.models import Student
from .models import (
    Enfermedad, Alergia, Lesion, CertificadoMedico, ContactoEmergencia
)
from .forms import (
    EnfermedadForm, AlergiaForm, LesionForm,
    CertificadoMedicoForm, ContactoEmergenciaForm
)


# ============================================================
# HELPERS
# ============================================================
def _log(user, accion, modelo, obj_id, descripcion, request):
    AuditLog.objects.create(
        usuario=user,
        accion=accion,
        modelo_afectado=modelo,
        objeto_id=str(obj_id),
        descripcion=descripcion,
        ip_address=request.META.get('REMOTE_ADDR'),
    )


# ============================================================
# PANEL CENTRAL DE SALUD
# ============================================================
@instructor_required
def health_dashboard(request):
    """
    Panel de salud con alertas críticas:
    - Certificados vencidos / por vencer
    - Alumnos con alergias graves
    - Alumnos con lesiones activas
    - Alumnos con enfermedades graves
    """
    hoy = timezone.now().date()

    # Certificados vencidos
    certificados_vencidos = (
        CertificadoMedico.objects
        .filter(fecha_vencimiento__lt=hoy)
        .select_related('alumno')
        .order_by('fecha_vencimiento')
    )

    # Certificados por vencer (30 días)
    certificados_por_vencer = (
        CertificadoMedico.objects
        .por_vencer(30)
        .select_related('alumno')
        .order_by('fecha_vencimiento')
    )

    # Alumnos activos SIN certificado
    alumnos_sin_certificado = (
        Student.objects
        .filter(estado='ACTIVO', certificado_medico__isnull=True)
        .order_by('apellido', 'nombre')
    )

    # Alergias graves activas
    alergias_graves = (
        Alergia.objects
        .filter(severidad='GRAVE', activa=True)
        .select_related('alumno')
    )

    # Alergias que requieren EpiPen
    epipen = (
        Alergia.objects
        .filter(requiere_epipen=True, activa=True)
        .select_related('alumno')
    )

    # Lesiones activas / en recuperación
    lesiones_activas = (
        Lesion.objects
        .filter(estado__in=['ACTIVA', 'EN_RECUPERACION'])
        .select_related('alumno')
        .order_by('-fecha_lesion')
    )

    # Enfermedades graves activas
    enfermedades_graves = (
        Enfermedad.objects
        .filter(gravedad='GRAVE', activa=True)
        .select_related('alumno')
    )

    context = {
        'certificados_vencidos': certificados_vencidos,
        'certificados_por_vencer': certificados_por_vencer,
        'alumnos_sin_certificado': alumnos_sin_certificado,
        'alergias_graves': alergias_graves,
        'epipen': epipen,
        'lesiones_activas': lesiones_activas,
        'enfermedades_graves': enfermedades_graves,
        'total_alertas': (
            certificados_vencidos.count()
            + certificados_por_vencer.count()
            + alergias_graves.count()
            + lesiones_activas.count()
        ),
    }
    return render(request, 'salud/dashboard.html', context)


# ============================================================
# ENFERMEDADES
# ============================================================
@admin_required
def enfermedad_create(request, alumno_pk):
    alumno = get_object_or_404(Student, pk=alumno_pk)
    form = EnfermedadForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.alumno = alumno
        obj.save()

        _log(request.user, 'CREAR', 'Enfermedad', obj.pk,
             f'Registró enfermedad "{obj.nombre}" para {alumno}', request)

        messages.success(request, f'Enfermedad "{obj.nombre}" registrada.')
        return redirect(f"{request.build_absolute_uri('/')[:-1]}/alumnos/{alumno.pk}/#salud")

    return render(request, 'salud/enfermedad_form.html', {
        'form': form, 'alumno': alumno, 'titulo': 'Nueva enfermedad',
    })


@admin_required
def enfermedad_update(request, pk):
    obj = get_object_or_404(Enfermedad, pk=pk)
    form = EnfermedadForm(request.POST or None, instance=obj)

    if request.method == 'POST' and form.is_valid():
        form.save()
        _log(request.user, 'EDITAR', 'Enfermedad', obj.pk,
             f'Editó enfermedad "{obj.nombre}" de {obj.alumno}', request)
        messages.success(request, 'Enfermedad actualizada.')
        return redirect('student_detail', pk=obj.alumno.pk)

    return render(request, 'salud/enfermedad_form.html', {
        'form': form, 'alumno': obj.alumno,
        'titulo': f'Editar: {obj.nombre}', 'objeto': obj,
    })


@admin_required
@require_http_methods(['POST'])
def enfermedad_delete(request, pk):
    obj = get_object_or_404(Enfermedad, pk=pk)
    alumno_pk = obj.alumno.pk
    nombre = obj.nombre
    obj.delete()

    _log(request.user, 'ELIMINAR', 'Enfermedad', pk,
         f'Eliminó enfermedad "{nombre}"', request)

    messages.success(request, f'Enfermedad "{nombre}" eliminada.')
    return redirect('student_detail', pk=alumno_pk)


# ============================================================
# ALERGIAS
# ============================================================
@admin_required
def alergia_create(request, alumno_pk):
    alumno = get_object_or_404(Student, pk=alumno_pk)
    form = AlergiaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.alumno = alumno
        obj.save()

        _log(request.user, 'CREAR', 'Alergia', obj.pk,
             f'Registró alergia "{obj.descripcion}" para {alumno}', request)

        messages.success(request, f'Alergia "{obj.descripcion}" registrada.')
        return redirect('student_detail', pk=alumno.pk)

    return render(request, 'salud/alergia_form.html', {
        'form': form, 'alumno': alumno, 'titulo': 'Nueva alergia',
    })


@admin_required
def alergia_update(request, pk):
    obj = get_object_or_404(Alergia, pk=pk)
    form = AlergiaForm(request.POST or None, instance=obj)

    if request.method == 'POST' and form.is_valid():
        form.save()
        _log(request.user, 'EDITAR', 'Alergia', obj.pk,
             f'Editó alergia "{obj.descripcion}" de {obj.alumno}', request)
        messages.success(request, 'Alergia actualizada.')
        return redirect('student_detail', pk=obj.alumno.pk)

    return render(request, 'salud/alergia_form.html', {
        'form': form, 'alumno': obj.alumno,
        'titulo': f'Editar alergia', 'objeto': obj,
    })


@admin_required
@require_http_methods(['POST'])
def alergia_delete(request, pk):
    obj = get_object_or_404(Alergia, pk=pk)
    alumno_pk = obj.alumno.pk
    descripcion = obj.descripcion
    obj.delete()

    _log(request.user, 'ELIMINAR', 'Alergia', pk,
         f'Eliminó alergia "{descripcion}"', request)

    messages.success(request, f'Alergia eliminada.')
    return redirect('student_detail', pk=alumno_pk)


# ============================================================
# LESIONES
# ============================================================
@admin_required
def lesion_create(request, alumno_pk):
    alumno = get_object_or_404(Student, pk=alumno_pk)
    form = LesionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.alumno = alumno
        obj.save()

        _log(request.user, 'CREAR', 'Lesion', obj.pk,
             f'Registró lesión en {obj.get_zona_cuerpo_display()} para {alumno}',
             request)

        messages.success(request, f'Lesión registrada.')
        return redirect('student_detail', pk=alumno.pk)

    return render(request, 'salud/lesion_form.html', {
        'form': form, 'alumno': alumno, 'titulo': 'Nueva lesión',
    })


@admin_required
def lesion_update(request, pk):
    obj = get_object_or_404(Lesion, pk=pk)
    form = LesionForm(request.POST or None, instance=obj)

    if request.method == 'POST' and form.is_valid():
        form.save()
        _log(request.user, 'EDITAR', 'Lesion', obj.pk,
             f'Editó lesión de {obj.alumno}', request)
        messages.success(request, 'Lesión actualizada.')
        return redirect('student_detail', pk=obj.alumno.pk)

    return render(request, 'salud/lesion_form.html', {
        'form': form, 'alumno': obj.alumno,
        'titulo': f'Editar lesión', 'objeto': obj,
    })


@admin_required
@require_http_methods(['POST'])
def lesion_delete(request, pk):
    obj = get_object_or_404(Lesion, pk=pk)
    alumno_pk = obj.alumno.pk
    obj.delete()

    _log(request.user, 'ELIMINAR', 'Lesion', pk,
         f'Eliminó lesión', request)

    messages.success(request, 'Lesión eliminada.')
    return redirect('student_detail', pk=alumno_pk)


# ============================================================
# CERTIFICADO MÉDICO (OneToOne)
# ============================================================
@admin_required
def certificado_create_or_update(request, alumno_pk):
    """
    Como es OneToOne, esta vista crea o edita el certificado del alumno.
    """
    alumno = get_object_or_404(Student, pk=alumno_pk)

    try:
        instancia = alumno.certificado_medico
    except CertificadoMedico.DoesNotExist:
        instancia = None

    form = CertificadoMedicoForm(
        request.POST or None,
        request.FILES or None,
        instance=instancia,
    )

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.alumno = alumno
        obj.save()

        accion = 'EDITAR' if instancia else 'CREAR'
        _log(request.user, accion, 'CertificadoMedico', obj.pk,
             f'{accion.title()} certificado médico de {alumno}', request)

        messages.success(request, 'Certificado médico guardado correctamente.')
        return redirect('student_detail', pk=alumno.pk)

    return render(request, 'salud/certificado_form.html', {
        'form': form,
        'alumno': alumno,
        'titulo': 'Editar certificado médico' if instancia else 'Subir certificado médico',
        'certificado': instancia,
    })


@admin_required
@require_http_methods(['POST'])
def certificado_delete(request, pk):
    obj = get_object_or_404(CertificadoMedico, pk=pk)
    alumno_pk = obj.alumno.pk
    obj.delete()

    _log(request.user, 'ELIMINAR', 'CertificadoMedico', pk,
         f'Eliminó certificado médico de {obj.alumno}', request)

    messages.success(request, 'Certificado eliminado.')
    return redirect('student_detail', pk=alumno_pk)


# ============================================================
# CONTACTO DE EMERGENCIA (OneToOne)
# ============================================================
@admin_required
def contacto_create_or_update(request, alumno_pk):
    alumno = get_object_or_404(Student, pk=alumno_pk)

    try:
        instancia = alumno.contacto_emergencia
    except ContactoEmergencia.DoesNotExist:
        instancia = None

    form = ContactoEmergenciaForm(request.POST or None, instance=instancia)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.alumno = alumno
        obj.save()

        accion = 'EDITAR' if instancia else 'CREAR'
        _log(request.user, accion, 'ContactoEmergencia', obj.pk,
             f'{accion.title()} contacto de emergencia de {alumno}', request)

        messages.success(request, 'Contacto de emergencia guardado.')
        return redirect('student_detail', pk=alumno.pk)

    return render(request, 'salud/contacto_form.html', {
        'form': form,
        'alumno': alumno,
        'titulo': 'Editar contacto de emergencia' if instancia else 'Nuevo contacto de emergencia',
        'contacto': instancia,
    })