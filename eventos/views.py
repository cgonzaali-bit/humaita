
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db import transaction
from decimal import Decimal

from usuarios.decorators import admin_required, instructor_required
from usuarios.models import AuditLog
from alumnos.models import Student
from .models import Evento, InscripcionEvento, FotoEvento
from .forms import (
    EventoForm, InscripcionForm, InscripcionMasivaForm,
    ResultadoForm, FotoEventoForm,
)


def _log(user, accion, modelo, obj_id, descripcion, request):
    AuditLog.objects.create(
        usuario=user, accion=accion, modelo_afectado=modelo,
        objeto_id=str(obj_id), descripcion=descripcion,
        ip_address=request.META.get('REMOTE_ADDR'),
    )


# ============================================================
# LISTADO DE EVENTOS
# ============================================================
@instructor_required
def evento_list(request):
    tab = request.GET.get('tab', 'proximos')

    if tab == 'pasados':
        qs = Evento.objects.pasados()
    else:
        qs = Evento.objects.proximos()

    # Filtro por tipo
    tipo = request.GET.get('tipo', '')
    if tipo:
        qs = qs.filter(tipo=tipo)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'tab': tab,
        'tipo': tipo,
        'tipos': Evento.Tipo.choices,
        'total_proximos': Evento.objects.proximos().count(),
        'total_pasados': Evento.objects.pasados().count(),
    }
    return render(request, 'eventos/evento_list.html', context)


# ============================================================
# DETALLE DE EVENTO
# ============================================================
@instructor_required
def evento_detail(request, pk):
    evento = get_object_or_404(Evento, pk=pk)

    inscripciones = evento.inscripciones.select_related('alumno') \
        .order_by('alumno__apellido', 'alumno__nombre')

    # Stats
    total_pagado = inscripciones.filter(estado_pago='PAGADO') \
        .aggregate(t=Sum('monto_pagado'))['t'] or Decimal('0')
    total_pendiente = inscripciones.filter(estado_pago='PENDIENTE') \
        .aggregate(t=Sum('monto_pagado'))['t'] or Decimal('0')

    # Resultados (si es competencia)
    con_resultado = inscripciones.filter(resultado__gt='').exclude(resultado='')

    context = {
        'evento': evento,
        'inscripciones': inscripciones,
        'total_pagado': total_pagado,
        'total_pendiente': total_pendiente,
        'con_resultado': con_resultado,
        'fotos': evento.fotos.all(),
    }
    return render(request, 'eventos/evento_detail.html', context)


# ============================================================
# CRUD DE EVENTOS
# ============================================================
@admin_required
def evento_create(request):
    form = EventoForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.creado_por = request.user
        obj.save()

        _log(request.user, 'CREAR', 'Evento', obj.pk,
             f'Creó evento "{obj.nombre}"', request)

        messages.success(request, f'Evento "{obj.nombre}" creado.')
        return redirect('evento_detail', pk=obj.pk)

    return render(request, 'eventos/evento_form.html', {
        'form': form, 'titulo': 'Nuevo evento',
    })


@admin_required
def evento_update(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    form = EventoForm(request.POST or None, instance=evento)

    if request.method == 'POST' and form.is_valid():
        form.save()
        _log(request.user, 'EDITAR', 'Evento', evento.pk,
             f'Editó evento "{evento.nombre}"', request)
        messages.success(request, 'Evento actualizado.')
        return redirect('evento_detail', pk=evento.pk)

    return render(request, 'eventos/evento_form.html', {
        'form': form, 'titulo': f'Editar: {evento.nombre}', 'evento': evento,
    })


@admin_required
@require_http_methods(['POST'])
def evento_delete(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    nombre = evento.nombre
    evento.delete()
    _log(request.user, 'ELIMINAR', 'Evento', pk,
         f'Eliminó evento "{nombre}"', request)
    messages.success(request, f'Evento "{nombre}" eliminado.')
    return redirect('evento_list')


# ============================================================
# INSCRIPCIONES
# ============================================================
@admin_required
def inscripcion_create(request, evento_pk):
    evento = get_object_or_404(Evento, pk=evento_pk)

    if evento.esta_lleno:
        messages.error(request, 'Este evento ya alcanzó su cupo máximo.')
        return redirect('evento_detail', pk=evento.pk)

    form = InscripcionForm(request.POST or None, evento=evento)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.evento = evento
        obj.save()

        _log(request.user, 'CREAR', 'InscripcionEvento', obj.pk,
             f'Inscribió a {obj.alumno} en "{evento.nombre}"', request)

        messages.success(request, f'{obj.alumno} inscrito en "{evento.nombre}".')
        return redirect('evento_detail', pk=evento.pk)

    return render(request, 'eventos/inscripcion_form.html', {
        'form': form, 'evento': evento,
    })


@admin_required
def inscripcion_masiva(request, evento_pk):
    """Inscribir varios alumnos a la vez."""
    evento = get_object_or_404(Evento, pk=evento_pk)
    form = InscripcionMasivaForm(request.POST or None, evento=evento)

    if request.method == 'POST' and form.is_valid():
        alumnos = form.cleaned_data['alumnos']
        eximir = form.cleaned_data['eximir_pago']

        creados = 0
        with transaction.atomic():
            for alumno in alumnos:
                InscripcionEvento.objects.create(
                    evento=evento,
                    alumno=alumno,
                    estado_pago='EXIMIDO' if eximir else 'PENDIENTE',
                    monto_pagado=Decimal('0') if eximir else evento.costo,
                )
                creados += 1

        _log(request.user, 'CREAR', 'InscripcionEvento', evento.pk,
             f'Inscribió {creados} alumnos en "{evento.nombre}"', request)

        messages.success(request, f'{creados} alumnos inscritos.')
        return redirect('evento_detail', pk=evento.pk)

    return render(request, 'eventos/inscripcion_masiva.html', {
        'form': form, 'evento': evento,
    })


@admin_required
@require_http_methods(['POST'])
def inscripcion_marcar_pagado(request, pk):
    insc = get_object_or_404(InscripcionEvento, pk=pk)
    if insc.estado_pago == 'PAGADO':
        messages.info(request, 'Esta inscripción ya estaba pagada.')
        return redirect('evento_detail', pk=insc.evento.pk)

    insc.estado_pago = 'PAGADO'
    if insc.monto_pagado == 0:
        insc.monto_pagado = insc.evento.costo
    if not insc.fecha_pago:
        insc.fecha_pago = timezone.now().date()
    insc.save()

    _log(request.user, 'PAGO', 'InscripcionEvento', insc.pk,
         f'Marcó pago de inscripción: {insc.alumno} en "{insc.evento.nombre}"',
         request)

    messages.success(request, 'Pago de inscripción registrado.')
    return redirect('evento_detail', pk=insc.evento.pk)


@admin_required
@require_http_methods(['POST'])
def inscripcion_delete(request, pk):
    insc = get_object_or_404(InscripcionEvento, pk=pk)
    evento_pk = insc.evento.pk
    nombre = str(insc.alumno)
    insc.delete()
    messages.success(request, f'Inscripción de {nombre} eliminada.')
    return redirect('evento_detail', pk=evento_pk)


# ============================================================
# RESULTADOS
# ============================================================
@admin_required
def resultado_update(request, pk):
    insc = get_object_or_404(InscripcionEvento, pk=pk)
    form = ResultadoForm(request.POST or None, instance=insc)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Resultado guardado.')
        return redirect('evento_detail', pk=insc.evento.pk)

    return render(request, 'eventos/resultado_form.html', {
        'form': form, 'inscripcion': insc,
    })


# ============================================================
# FOTOS DEL EVENTO
# ============================================================
@admin_required
def foto_upload(request, evento_pk):
    evento = get_object_or_404(Evento, pk=evento_pk)
    form = FotoEventoForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.evento = evento
        obj.save()
        messages.success(request, 'Foto subida.')
        return redirect('evento_detail', pk=evento.pk)

    return render(request, 'eventos/foto_form.html', {
        'form': form, 'evento': evento,
    })


@admin_required
@require_http_methods(['POST'])
def foto_delete(request, pk):
    foto = get_object_or_404(FotoEvento, pk=pk)
    evento_pk = foto.evento.pk
    foto.delete()
    messages.success(request, 'Foto eliminada.')
    return redirect('evento_detail', pk=evento_pk)