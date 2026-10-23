
from decimal import Decimal
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import HttpResponse, FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db import transaction

from usuarios.decorators import admin_required, instructor_required
from usuarios.models import AuditLog
from alumnos.models import Student
from .models import PlanPago, Pago, Promocion
from .forms import (
    PlanPagoForm, PagoForm, PagoRapidoForm,
    GenerarMensualidadesForm, PromocionForm,
)
from .utils import generar_recibo_pdf, generar_reporte_recaudacion_pdf


# ============================================================
# HELPERS
# ============================================================
def _log(user, accion, modelo, obj_id, descripcion, request):
    AuditLog.objects.create(
        usuario=user, accion=accion, modelo_afectado=modelo,
        objeto_id=str(obj_id), descripcion=descripcion,
        ip_address=request.META.get('REMOTE_ADDR'),
    )


MESES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]


# ============================================================
# DASHBOARD DE PAGOS
# ============================================================
@admin_required
def payments_dashboard(request):
    """
    Panel principal de pagos con KPIs:
    - Recaudación del mes actual vs mes anterior
    - Total pagado y pendiente
    - Alumnos morosos
    - Próximos vencimientos
    """
    hoy = timezone.now().date()

    # KPIs del mes actual
    mes_actual = hoy.month
    anio_actual = hoy.year

    pagos_mes_actual = Pago.objects.del_periodo(mes_actual, anio_actual)
    total_pagado_mes = pagos_mes_actual.pagados().aggregate(
        t=Sum('monto_final')
    )['t'] or Decimal('0')
    total_pendiente_mes = pagos_mes_actual.filter(
        estado__in=['PENDIENTE', 'ATRASADO']
    ).aggregate(t=Sum('monto_final'))['t'] or Decimal('0')

    # Mes anterior
    if mes_actual == 1:
        mes_ant, anio_ant = 12, anio_actual - 1
    else:
        mes_ant, anio_ant = mes_actual - 1, anio_actual

    total_pagado_mes_ant = Pago.objects.del_periodo(mes_ant, anio_ant) \
        .pagados().aggregate(t=Sum('monto_final'))['t'] or Decimal('0')

    variacion = Decimal('0')
    if total_pagado_mes_ant > 0:
        variacion = (
            (total_pagado_mes - total_pagado_mes_ant)
            / total_pagado_mes_ant * 100
        )

    # Morosos (pagos atrasados)
    morosos = Pago.objects.atrasados().select_related('alumno') \
        .order_by('fecha_vencimiento')

    # Próximos vencimientos (5 días)
    proximos_vencimientos = Pago.objects.filter(
        estado__in=['PENDIENTE', 'ATRASADO'],
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timezone.timedelta(days=5),
    ).select_related('alumno').order_by('fecha_vencimiento')

    # Recaudación últimos 12 meses
    recaudacion_mensual = []
    for i in range(11, -1, -1):
        m = hoy.month - i
        y = hoy.year
        while m <= 0:
            m += 12
            y -= 1
        total = Pago.objects.del_periodo(m, y).pagados() \
            .aggregate(t=Sum('monto_final'))['t'] or Decimal('0')
        recaudacion_mensual.append({
            'label': f'{MESES[m][:3]} {str(y)[2:]}',
            'total': float(total),
        })

    # Pagos recientes
    pagos_recientes = Pago.objects.pagados() \
        .select_related('alumno', 'plan') \
        .order_by('-fecha_pago', '-actualizado_en')[:8]

    context = {
        'total_pagado_mes': total_pagado_mes,
        'total_pagado_mes_ant': total_pagado_mes_ant,
        'total_pendiente_mes': total_pendiente_mes,
        'variacion': variacion,
        'morosos': morosos[:10],
        'morosos_count': morosos.count(),
        'proximos_vencimientos': proximos_vencimientos,
        'recaudacion_mensual': recaudacion_mensual,
        'pagos_recientes': pagos_recientes,
        'mes_actual': MESES[mes_actual],
        'anio_actual': anio_actual,
    }
    return render(request, 'pagos/dashboard.html', context)


# ============================================================
# DETALLES DE PLANES 
# ============================================================


@instructor_required
def api_plan_detalle(request, pk):
    """Devuelve el monto de un plan para autocompletar formularios."""
    plan = get_object_or_404(PlanPago, pk=pk)
    return JsonResponse({
        'id': plan.pk,
        'nombre': plan.nombre,
        'monto': float(plan.monto),
    })

# ============================================================
# PLANES DE PAGO (CRUD)
# ============================================================
@admin_required
def plan_list(request):
    planes = PlanPago.objects.all().annotate(
        num_pagos=Count('pagos')
    ).order_by('tipo_alumno', 'monto')
    return render(request, 'pagos/plan_list.html', {'planes': planes})


@admin_required
def plan_create(request):
    form = PlanPagoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        _log(request.user, 'CREAR', 'PlanPago', obj.pk,
             f'Creó plan "{obj.nombre}"', request)
        messages.success(request, f'Plan "{obj.nombre}" creado.')
        return redirect('plan_list')
    return render(request, 'pagos/plan_form.html', {
        'form': form, 'titulo': 'Nuevo plan de pago',
    })


@admin_required
def plan_update(request, pk):
    obj = get_object_or_404(PlanPago, pk=pk)
    form = PlanPagoForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        _log(request.user, 'EDITAR', 'PlanPago', obj.pk,
             f'Editó plan "{obj.nombre}"', request)
        messages.success(request, 'Plan actualizado.')
        return redirect('plan_list')
    return render(request, 'pagos/plan_form.html', {
        'form': form, 'titulo': f'Editar: {obj.nombre}', 'objeto': obj,
    })


@admin_required
@require_http_methods(['POST'])
def plan_delete(request, pk):
    obj = get_object_or_404(PlanPago, pk=pk)
    if obj.pagos.exists():
        messages.error(
            request,
            'No se puede eliminar: hay pagos asociados. Desactívalo en su lugar.'
        )
        return redirect('plan_list')
    nombre = obj.nombre
    obj.delete()
    messages.success(request, f'Plan "{nombre}" eliminado.')
    return redirect('plan_list')


# ============================================================
# PAGOS (CRUD + Registro + Recibo)
# ============================================================
@admin_required
def pago_list(request):
    qs = Pago.objects.select_related('alumno', 'plan').order_by('-anio', '-mes')

    # Filtros
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    mes = request.GET.get('mes', '')
    anio = request.GET.get('anio', '')

    if q:
        qs = qs.filter(
            Q(alumno__nombre__icontains=q)
            | Q(alumno__apellido__icontains=q)
            | Q(alumno__dni__icontains=q)
            | Q(numero_recibo__icontains=q)
        )
    if estado:
        qs = qs.filter(estado=estado)
    if mes:
        qs = qs.filter(mes=mes)
    if anio:
        qs = qs.filter(anio=anio)

    # Stats
    total_filtrado = qs.aggregate(t=Sum('monto_final'))['t'] or Decimal('0')

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'estados': Pago.Estado.choices,
        'anios': range(timezone.now().year, timezone.now().year - 5, -1),
        'total_filtrado': total_filtrado,
        'q': q, 'estado': estado, 'mes_f': mes, 'anio_f': anio,
        'meses': list(enumerate(MESES))[1:],
    }
    return render(request, 'pagos/pago_list.html', context)


@admin_required
def pago_create(request):
    """Registrar un pago (por defecto se marca PAGADO)."""
    initial = {}
    if request.GET.get('alumno'):
        initial['alumno'] = request.GET['alumno']
    if request.GET.get('plan'):
        initial['plan'] = request.GET['plan']
        try:
            plan = PlanPago.objects.get(pk=request.GET['plan'])
            initial['monto'] = plan.monto
        except PlanPago.DoesNotExist:
            pass
    initial['estado'] = Pago.Estado.PAGADO
    initial['fecha_pago'] = timezone.now().date()

    form = PagoForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.registrado_por = request.user
        obj.save()

        _log(request.user, 'PAGO', 'Pago', obj.pk,
             f'Registró pago de {obj.alumno} por ${obj.monto_final} '
             f'({obj.periodo_display})', request)

        messages.success(
            request,
            f'Pago registrado. Recibo N° {obj.numero_recibo or "—"}'
        )

        # Si pidió recibo, redirige a descargar
        if request.POST.get('descargar_recibo'):
            return redirect('pago_recibo_pdf', pk=obj.pk)

        return redirect('pago_detail', pk=obj.pk)

    return render(request, 'pagos/pago_form.html', {
        'form': form, 'titulo': 'Registrar pago', 'accion': 'Registrar',
    })


@admin_required
def pago_update(request, pk):
    obj = get_object_or_404(Pago, pk=pk)
    form = PagoForm(request.POST or None, instance=obj)

    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        if not obj.registrado_por:
            obj.registrado_por = request.user
        obj.save()

        _log(request.user, 'EDITAR', 'Pago', obj.pk,
             f'Editó pago de {obj.alumno}', request)
        messages.success(request, 'Pago actualizado.')
        return redirect('pago_detail', pk=obj.pk)

    return render(request, 'pagos/pago_form.html', {
        'form': form, 'titulo': f'Editar pago de {obj.alumno}',
        'accion': 'Guardar', 'objeto': obj,
    })


@admin_required
def pago_detail(request, pk):
    obj = get_object_or_404(
        Pago.objects.select_related('alumno', 'plan', 'registrado_por'),
        pk=pk,
    )
    return render(request, 'pagos/pago_detail.html', {'pago': obj})


@admin_required
def pago_recibo_pdf(request, pk):
    """Genera y descarga el PDF del recibo."""
    obj = get_object_or_404(
        Pago.objects.select_related('alumno', 'plan'), pk=pk
    )

    if obj.estado != Pago.Estado.PAGADO:
        messages.warning(
            request,
            'Solo se pueden generar recibos de pagos con estado PAGADO.'
        )
        return redirect('pago_detail', pk=obj.pk)

    buffer = generar_recibo_pdf(obj)
    filename = f'recibo_{obj.numero_recibo or obj.pk}.pdf'

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@admin_required
@require_http_methods(['POST'])
def pago_marcar_pagado(request, pk):
    """Marca un pago pendiente como PAGADO rápidamente."""
    obj = get_object_or_404(Pago, pk=pk)
    if obj.estado == Pago.Estado.PAGADO:
        messages.info(request, 'Este pago ya estaba registrado como pagado.')
        return redirect('pago_detail', pk=obj.pk)

    obj.estado = Pago.Estado.PAGADO
    obj.fecha_pago = timezone.now().date()
    if not obj.metodo_pago:
        obj.metodo_pago = Pago.Metodo.EFECTIVO
    obj.registrado_por = request.user
    obj.save()

    _log(request.user, 'PAGO', 'Pago', obj.pk,
         f'Marcó como pagado: {obj.alumno} - ${obj.monto_final}', request)

    messages.success(request, f'Pago marcado como PAGADO. Recibo {obj.numero_recibo}.')
    return redirect('pago_detail', pk=obj.pk)


@admin_required
@require_http_methods(['POST'])
def pago_delete(request, pk):
    obj = get_object_or_404(Pago, pk=pk)
    alumno_nombre = str(obj.alumno)
    periodo = obj.periodo_display
    obj.delete()
    _log(request.user, 'ELIMINAR', 'Pago', pk,
         f'Eliminó pago de {alumno_nombre} ({periodo})', request)
    messages.success(request, 'Pago eliminado.')
    return redirect('pago_list')


# ============================================================
# GENERACIÓN MASIVA DE MENSUALIDADES
# ============================================================
@admin_required
def generar_mensualidades(request):
    """
    Genera automáticamente los registros PENDIENTES de mensualidad
    para todos los alumnos activos en un mes/año dado.
    """
    form = GenerarMensualidadesForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        mes = int(form.cleaned_data['mes'])
        anio = form.cleaned_data['anio']
        incluir_inactivos = form.cleaned_data['incluir_inactivos']

        estados = ['ACTIVO', 'CONGELADO']
        if incluir_inactivos:
            estados.append('INACTIVO')

        alumnos = Student.objects.filter(estado__in=estados)
        creados = 0
        existentes = 0
        sin_plan = []

        with transaction.atomic():
            for alumno in alumnos:
                # Buscar plan por categoría
                plan = PlanPago.objects.filter(
                    activo=True, tipo_alumno=alumno.categoria
                ).first()

                if not plan:
                    plan = PlanPago.objects.filter(
                        activo=True, tipo_alumno='TODOS'
                    ).first()

                if not plan:
                    sin_plan.append(str(alumno))
                    continue

                # ¿Ya existe el pago?
                if Pago.objects.filter(alumno=alumno, mes=mes, anio=anio).exists():
                    existentes += 1
                    continue

                Pago.objects.create(
                    alumno=alumno,
                    plan=plan,
                    mes=mes,
                    anio=anio,
                    monto=plan.monto,
                    estado=Pago.Estado.PENDIENTE,
                )
                creados += 1

        mensaje = f'Se crearon {creados} mensualidades nuevas.'
        if existentes:
            mensaje += f' {existentes} ya existían.'
        if sin_plan:
            mensaje += f' {len(sin_plan)} alumnos sin plan asignado.'

        messages.success(request, mensaje)

        if sin_plan:
            messages.warning(
                request,
                f'Alumnos sin plan: {", ".join(sin_plan[:5])}'
                + ('...' if len(sin_plan) > 5 else '')
            )

        return redirect(f'/pagos/?mes={mes}&anio={anio}')

    return render(request, 'pagos/generar_mensualidades.html', {'form': form})


# ============================================================
# PANEL DE MOROSOS
# ============================================================
@admin_required
def morosos(request):
    """Listado de alumnos con pagos pendientes o atrasados."""
    qs = Pago.objects.atrasados().select_related('alumno', 'plan') \
        .order_by('fecha_vencimiento')

    # Agrupar por alumno
    por_alumno = {}
    for p in qs:
        key = p.alumno_id
        if key not in por_alumno:
            por_alumno[key] = {
                'alumno': p.alumno,
                'pagos': [],
                'total_deuda': Decimal('0'),
            }
        por_alumno[key]['pagos'].append(p)
        por_alumno[key]['total_deuda'] += p.monto_final

    # Ordenar por deuda descendente
    lista = sorted(
        por_alumno.values(),
        key=lambda x: x['total_deuda'],
        reverse=True,
    )

    total_general = sum((a['total_deuda'] for a in lista), Decimal('0'))

    return render(request, 'pagos/morosos.html', {
        'morosos': lista,
        'total_general': total_general,
    })


# ============================================================
# REPORTES
# ============================================================
@admin_required
def reporte_recaudacion(request):
    """Reporte de recaudación por rango de fechas."""
    hoy = timezone.now().date()

    # Por defecto: mes actual
    desde = request.GET.get('desde', hoy.replace(day=1).isoformat())
    hasta = request.GET.get('hasta', hoy.isoformat())

    try:
        desde_dt = date.fromisoformat(desde)
        hasta_dt = date.fromisoformat(hasta)
    except (ValueError, TypeError):
        desde_dt = hoy.replace(day=1)
        hasta_dt = hoy

    pagos = Pago.objects.pagados().filter(
        fecha_pago__gte=desde_dt,
        fecha_pago__lte=hasta_dt,
    ).select_related('alumno', 'plan').order_by('fecha_pago')

    total = pagos.aggregate(t=Sum('monto_final'))['t'] or Decimal('0')

    # Desglose por método de pago
    por_metodo = pagos.values('metodo_pago').annotate(
        total=Sum('monto_final'),
        cantidad=Count('id'),
    ).order_by('-total')

    # Mapear a etiquetas legibles
    metodos_map = dict(Pago.Metodo.choices)
    for item in por_metodo:
        item['metodo_display'] = metodos_map.get(
            item['metodo_pago'], item['metodo_pago'] or '—'
        )

    context = {
        'pagos': pagos,
        'total': total,
        'por_metodo': por_metodo,
        'desde': desde_dt.isoformat(),
        'hasta': hasta_dt.isoformat(),
        'cantidad': pagos.count(),
    }
    return render(request, 'pagos/reporte_recaudacion.html', context)


@admin_required
def reporte_recaudacion_pdf(request):
    """Exporta el reporte de recaudación a PDF."""
    hoy = timezone.now().date()
    desde = request.GET.get('desde', hoy.replace(day=1).isoformat())
    hasta = request.GET.get('hasta', hoy.isoformat())

    desde_dt = date.fromisoformat(desde)
    hasta_dt = date.fromisoformat(hasta)

    pagos = Pago.objects.pagados().filter(
        fecha_pago__gte=desde_dt,
        fecha_pago__lte=hasta_dt,
    ).select_related('alumno').order_by('fecha_pago')

    buffer = generar_reporte_recaudacion_pdf(
        pagos,
        'Reporte de Recaudación',
        f'Desde {desde_dt.strftime("%d/%m/%Y")} hasta {hasta_dt.strftime("%d/%m/%Y")}',
    )
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="recaudacion_{desde}_{hasta}.pdf"'
    )
    return response


# ============================================================
# PROMOCIONES (CRUD)
# ============================================================
@admin_required
def promocion_list(request):
    promos = Promocion.objects.all().order_by('-fecha_inicio')
    return render(request, 'pagos/promocion_list.html', {'promociones': promos})


@admin_required
def promocion_create(request):
    form = PromocionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Promoción creada.')
        return redirect('promocion_list')
    return render(request, 'pagos/promocion_form.html', {
        'form': form, 'titulo': 'Nueva promoción',
    })


@admin_required
def promocion_update(request, pk):
    obj = get_object_or_404(Promocion, pk=pk)
    form = PromocionForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Promoción actualizada.')
        return redirect('promocion_list')
    return render(request, 'pagos/promocion_form.html', {
        'form': form, 'titulo': f'Editar: {obj.nombre}', 'objeto': obj,
    })

