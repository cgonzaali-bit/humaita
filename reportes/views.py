from django.shortcuts import render

from decimal import Decimal
from datetime import date, timedelta
from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import (
    Sum, Count, Q, Avg, F, Case, When, IntegerField, Value
)
from django.db.models.functions import TruncMonth, Coalesce
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from usuarios.decorators import admin_required, instructor_required
from alumnos.models import Student
from salud.models import CertificadoMedico, Enfermedad, Alergia, Lesion
from pagos.models import Pago, PlanPago
from eventos.models import Evento, InscripcionEvento
from asistencia.models import Asistencia, Clase

from .utils import (
    exportar_alumnos_excel, exportar_recaudacion_excel,
    exportar_asistencia_excel, exportar_aptos_examen_excel,
)


MESES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]


# ============================================================
# DASHBOARD PRINCIPAL (Unificado)
# ============================================================
@instructor_required
def dashboard(request):
    """
    Dashboard global con KPIs de todos los módulos.
    Sobrescribe la vista `dashboard` de accounts para integrar todo.
    """
    hoy = timezone.now().date()
    mes_actual = hoy.month
    anio_actual = hoy.year
    inicio_mes = hoy.replace(day=1)
    hace_30_dias = hoy - timedelta(days=30)
    hace_90_dias = hoy - timedelta(days=90)

    # ===== ALUMNOS =====
    alumnos_activos = Student.objects.filter(estado='ACTIVO')
    total_alumnos = Student.objects.count()
    total_activos = alumnos_activos.count()

    # Por cinturón
    alumnos_por_cinturon = {
        c[0]: alumnos_activos.filter(cinturon_actual=c[0]).count()
        for c in Student.Cinturon.choices
    }

    # Por categoría
    alumnos_por_categoria = {
        c[0]: alumnos_activos.filter(categoria=c[0]).count()
        for c in Student.Categoria.choices
    }

    # Nuevos este mes
    nuevos_mes = Student.objects.filter(
        fecha_inicio__gte=inicio_mes
    ).count()

    # ===== PAGOS =====
    pagos_mes = Pago.objects.filter(mes=mes_actual, anio=anio_actual)
    total_cobrado = pagos_mes.filter(estado='PAGADO').aggregate(
        t=Sum('monto_final')
    )['t'] or Decimal('0')
    total_pendiente = pagos_mes.filter(
        estado__in=['PENDIENTE', 'ATRASADO']
    ).aggregate(t=Sum('monto_final'))['t'] or Decimal('0')
    total_atrasado = Pago.objects.filter(
        estado__in=['PENDIENTE', 'ATRASADO'],
        fecha_vencimiento__lt=hoy,
    ).aggregate(t=Sum('monto_final'))['t'] or Decimal('0')
    pagos_atrasados_count = Pago.objects.filter(
        estado__in=['PENDIENTE', 'ATRASADO'],
        fecha_vencimiento__lt=hoy,
    ).count()

    # Recaudación últimos 6 meses
    recaudacion_6m = []
    for i in range(5, -1, -1):
        m = mes_actual - i
        y = anio_actual
        while m <= 0:
            m += 12
            y -= 1
        total = Pago.objects.filter(mes=m, anio=y, estado='PAGADO').aggregate(
            t=Sum('monto_final')
        )['t'] or Decimal('0')
        recaudacion_6m.append({
            'label': f'{MESES[m][:3]} {str(y)[2:]}',
            'total': float(total),
        })

    # ===== SALUD =====
    certificados_vencidos = CertificadoMedico.objects.filter(
        fecha_vencimiento__lt=hoy
    ).count()
    certificados_por_vencer = CertificadoMedico.objects.filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=30),
    ).count()
    alumnos_sin_certificado = alumnos_activos.filter(
        certificado_medico__isnull=True
    ).count()
    lesiones_activas = Lesion.objects.filter(
        estado__in=['ACTIVA', 'EN_RECUPERACION']
    ).count()
    alergias_graves = Alergia.objects.filter(
        severidad='GRAVE', activa=True
    ).count()

    # ===== ASISTENCIA =====
    asistencias_mes = Asistencia.objects.filter(
        fecha__gte=inicio_mes, presente=True
    ).count()
    asistencias_30d = Asistencia.objects.filter(
        fecha__gte=hace_30_dias, presente=True
    ).count()

    # Tasa de asistencia (últimos 30 días)
    total_registros_30d = Asistencia.objects.filter(
        fecha__gte=hace_30_dias
    ).count()
    tasa_asistencia = 0
    if total_registros_30d > 0:
        tasa_asistencia = round(
            asistencias_30d / total_registros_30d * 100, 1
        )

    # Asistencia por día (últimos 7 días)
    asistencia_7d = []
    for i in range(6, -1, -1):
        d = hoy - timedelta(days=i)
        count = Asistencia.objects.filter(fecha=d, presente=True).count()
        asistencia_7d.append({
            'label': d.strftime('%a %d'),
            'total': count,
        })

    # ===== EVENTOS =====
    eventos_proximos = Evento.objects.proximos()[:5]
    eventos_pasados_mes = Evento.objects.pasados().filter(
        fecha__gte=inicio_mes
    ).count()

    # ===== ACTIVIDAD RECIENTE =====
    pagos_recientes = Pago.objects.pagados().select_related('alumno') \
        .order_by('-fecha_pago', '-actualizado_en')[:6]

    # ===== PRÓXIMOS VENCIMIENTOS =====
    proximos_vencimientos = Pago.objects.filter(
        estado__in=['PENDIENTE', 'ATRASADO'],
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=7),
    ).select_related('alumno').order_by('fecha_vencimiento')[:8]

    context = {
        # Alumnos
        'total_alumnos': total_alumnos,
        'total_activos': total_activos,
        'nuevos_mes': nuevos_mes,
        'alumnos_por_cinturon': alumnos_por_cinturon,
        'alumnos_por_categoria': alumnos_por_categoria,

        # Pagos
        'total_cobrado': total_cobrado,
        'total_pendiente': total_pendiente,
        'total_atrasado': total_atrasado,
        'pagos_atrasados_count': pagos_atrasados_count,
        'recaudacion_6m': recaudacion_6m,
        'pagos_recientes': pagos_recientes,
        'proximos_vencimientos': proximos_vencimientos,

        # Salud
        'certificados_vencidos': certificados_vencidos,
        'certificados_por_vencer': certificados_por_vencer,
        'alumnos_sin_certificado': alumnos_sin_certificado,
        'lesiones_activas': lesiones_activas,
        'alergias_graves': alergias_graves,

        # Asistencia
        'asistencias_mes': asistencias_mes,
        'tasa_asistencia': tasa_asistencia,
        'asistencia_7d': asistencia_7d,

        # Eventos
        'eventos_proximos': eventos_proximos,
        'eventos_pasados_mes': eventos_pasados_mes,

        # Meta
        'hoy': hoy,
        'mes_nombre': MESES[mes_actual],
    }
    return render(request, 'reportes/dashboard.html', context)


# ============================================================
# REPORTES
# ============================================================
@instructor_required
def reportes_index(request):
    """Página de inicio con tarjetas a los distintos reportes."""
    return render(request, 'reportes/index.html')


# -------- Reporte: Alumnos --------
@instructor_required
def reporte_alumnos(request):
    """Reporte de alumnos con filtros y exportación."""
    qs = Student.objects.all().order_by('apellido', 'nombre')

    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    cinturon = request.GET.get('cinturon', '')
    categoria = request.GET.get('categoria', '')

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(apellido__icontains=q)
            | Q(rut__icontains=q)
        )
    if estado:
        qs = qs.filter(estado=estado)
    if cinturon:
        qs = qs.filter(cinturon_actual=cinturon)
    if categoria:
        qs = qs.filter(categoria=categoria)

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'total': qs.count(),
        'q': q,
        'estado': estado,
        'cinturon': cinturon,
        'categoria': categoria,
        'estados': Student.Estado.choices,
        'cinturones': Student.Cinturon.choices,
        'categorias': Student.Categoria.choices,
    }
    return render(request, 'reportes/reporte_alumnos.html', context)


@admin_required
def reporte_alumnos_excel(request):
    """Exporta el listado de alumnos aplicando los mismos filtros."""
    qs = Student.objects.all().order_by('apellido', 'nombre')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(apellido__icontains=q)
            | Q(rut__icontains=q)
        )
    if request.GET.get('estado'):
        qs = qs.filter(estado=request.GET['estado'])
    if request.GET.get('cinturon'):
        qs = qs.filter(cinturon_actual=request.GET['cinturon'])
    if request.GET.get('categoria'):
        qs = qs.filter(categoria=request.GET['categoria'])

    buffer = exportar_alumnos_excel(qs)
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="alumnos_{timezone.now().date()}.xlsx"'
    )
    return response


# -------- Reporte: Recaudación --------
@instructor_required
def reporte_recaudacion_global(request):
    """Reporte de recaudación con comparativa mensual y rango personalizado."""
    hoy = timezone.now().date()

    # Rango por defecto: año actual
    desde = request.GET.get('desde', date(hoy.year, 1, 1).isoformat())
    hasta = request.GET.get('hasta', hoy.isoformat())

    try:
        desde_dt = date.fromisoformat(desde)
        hasta_dt = date.fromisoformat(hasta)
    except (ValueError, TypeError):
        desde_dt = date(hoy.year, 1, 1)
        hasta_dt = hoy

    pagos = Pago.objects.pagados().filter(
        fecha_pago__gte=desde_dt,
        fecha_pago__lte=hasta_dt,
    ).select_related('alumno', 'plan')

    total = pagos.aggregate(t=Sum('monto_final'))['t'] or Decimal('0')
    cantidad = pagos.count()
    promedio = total / cantidad if cantidad else Decimal('0')

    # Por método
    por_metodo = pagos.values('metodo_pago').annotate(
        total=Sum('monto_final'),
        cantidad=Count('id'),
    ).order_by('-total')
    metodos_map = dict(Pago.Metodo.choices)
    for item in por_metodo:
        item['metodo_display'] = metodos_map.get(
            item['metodo_pago'], item['metodo_pago'] or '—'
        )

    # Por plan
    por_plan = pagos.values('plan__nombre').annotate(
        total=Sum('monto_final'),
        cantidad=Count('id'),
    ).order_by('-total')

    # Comparativa por mes (dentro del rango)
    por_mes = pagos.annotate(
        mes_calc=TruncMonth('fecha_pago')
    ).values('mes_calc').annotate(
        total=Sum('monto_final'),
        cantidad=Count('id'),
    ).order_by('mes_calc')

    por_mes_data = [
        {
            'label': item['mes_calc'].strftime('%b %Y'),
            'total': float(item['total']),
            'cantidad': item['cantidad'],
        }
        for item in por_mes
    ]

    context = {
        'desde': desde_dt.isoformat(),
        'hasta': hasta_dt.isoformat(),
        'total': total,
        'cantidad': cantidad,
        'promedio': promedio,
        'por_metodo': por_metodo,
        'por_plan': por_plan,
        'por_mes_data': por_mes_data,
    }
    return render(request, 'reportes/reporte_recaudacion_global.html', context)


@admin_required
def reporte_recaudacion_global_excel(request):
    """Exporta el reporte de recaudación a Excel."""
    hoy = timezone.now().date()
    desde = request.GET.get('desde', date(hoy.year, 1, 1).isoformat())
    hasta = request.GET.get('hasta', hoy.isoformat())

    try:
        desde_dt = date.fromisoformat(desde)
        hasta_dt = date.fromisoformat(hasta)
    except (ValueError, TypeError):
        desde_dt = date(hoy.year, 1, 1)
        hasta_dt = hoy

    pagos = Pago.objects.pagados().filter(
        fecha_pago__gte=desde_dt,
        fecha_pago__lte=hasta_dt,
    ).select_related('alumno', 'plan').order_by('fecha_pago')

    buffer = exportar_recaudacion_excel(
        pagos,
        'Reporte de Recaudación',
        f'Desde {desde_dt.strftime("%d/%m/%Y")} hasta {hasta_dt.strftime("%d/%m/%Y")}',
    )
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="recaudacion_{desde}_{hasta}.xlsx"'
    )
    return response


# -------- Reporte: Asistencia --------
@instructor_required
def reporte_asistencia(request):
    """Reporte de asistencia con filtros y estadísticas."""
    qs = Asistencia.objects.select_related('alumno', 'clase') \
        .order_by('-fecha')

    q = request.GET.get('q', '').strip()
    clase_id = request.GET.get('clase_id', '')
    desde = request.GET.get('desde', '')
    hasta = request.GET.get('hasta', '')
    solo_presentes = request.GET.get('solo_presentes') == '1'

    if q:
        qs = qs.filter(
            Q(alumno__nombre__icontains=q)
            | Q(alumno__apellido__icontains=q)
        )
    if clase_id:
        qs = qs.filter(clase_id=clase_id)
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    if solo_presentes:
        qs = qs.filter(presente=True)

    # Estadísticas
    total = qs.count()
    presentes = qs.filter(presente=True).count()
    tasa = round(presentes / total * 100, 1) if total else 0

    # Top alumnos por asistencia
    top_alumnos = qs.filter(presente=True).values(
        'alumno__id', 'alumno__nombre', 'alumno__apellido'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:10]

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'total': total,
        'presentes': presentes,
        'tasa': tasa,
        'top_alumnos': top_alumnos,
        'clases': Clase.objects.activas(),
        'q': q,
        'clase_id': clase_id,
        'desde': desde,
        'hasta': hasta,
        'solo_presentes': solo_presentes,
    }
    return render(request, 'reportes/reporte_asistencia.html', context)


@admin_required
def reporte_asistencia_excel(request):
    """Exporta el reporte de asistencia a Excel."""
    qs = Asistencia.objects.select_related('alumno', 'clase').order_by('-fecha')

    if request.GET.get('q'):
        qs = qs.filter(
            Q(alumno__nombre__icontains=request.GET['q'])
            | Q(alumno__apellido__icontains=request.GET['q'])
        )
    if request.GET.get('clase_id'):
        qs = qs.filter(clase_id=request.GET['clase_id'])
    if request.GET.get('desde'):
        qs = qs.filter(fecha__gte=request.GET['desde'])
    if request.GET.get('hasta'):
        qs = qs.filter(fecha__lte=request.GET['hasta'])

    buffer = exportar_asistencia_excel(
        qs,
        'Reporte de Asistencia',
        f'{qs.count()} registros',
    )
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="asistencia_{timezone.now().date()}.xlsx"'
    )
    return response


# -------- Reporte: Aptos para examen de cinturón --------
@instructor_required
def reporte_aptos_examen(request):
    """
    Reporte avanzado: alumnos candidatos a examen de cinturón.
    Criterios configurables:
    - Mínimo de asistencias en los últimos 90 días
    - Certificado médico vigente
    - Sin lesiones activas que impidan entrenar
    - Tiempo mínimo desde la última promoción
    """
    hoy = timezone.now().date()
    hace_90_dias = hoy - timedelta(days=90)

    # Parámetros configurables
    min_asistencias = int(request.GET.get('min_asistencias', 24))
    cinturon_filtro = request.GET.get('cinturon', '')

    # Candidatos: alumnos activos
    qs = Student.objects.filter(estado='ACTIVO')

    if cinturon_filtro:
        qs = qs.filter(cinturon_actual=cinturon_filtro)

    # Calcular estadísticas por alumno
    alumnos_analisis = []
    for alumno in qs.select_related('certificado_medico'):
        # Asistencias en 90 días
        asistencias_90d = Asistencia.objects.filter(
            alumno=alumno,
            fecha__gte=hace_90_dias,
            presente=True,
        ).count()

        total_asistencias = Asistencia.objects.filter(
            alumno=alumno, presente=True
        ).count()

        # Certificado
        cert_estado = 'Sin certificado'
        cert_vigente = False
        try:
            cert = alumno.certificado_medico
            if cert.fecha_vencimiento >= hoy:
                cert_estado = f'Vigente ({cert.dias_para_vencer}d)'
                cert_vigente = True
            else:
                cert_estado = f'Vencido (hace {abs(cert.dias_para_vencer)}d)'
        except CertificadoMedico.DoesNotExist:
            pass

        # Lesiones activas
        lesiones_activas = alumno.lesiones.filter(
            estado__in=['ACTIVA', 'EN_RECUPERACION']
        ).count()

        # Tiempo desde última promoción
        ultima_promo = alumno.historial_cinturones.first()
        meses_desde_promo = None
        if ultima_promo:
            meses_desde_promo = (
                (hoy - ultima_promo.fecha_promocion).days // 30
            )

        # Determinar si es apto
        apto = (
            asistencias_90d >= min_asistencias
            and cert_vigente
            and lesiones_activas == 0
        )

        # Observaciones
        obs = []
        if asistencias_90d < min_asistencias:
            obs.append(f'Faltan {min_asistencias - asistencias_90d} asistencias')
        if not cert_vigente:
            obs.append('Certificado no vigente')
        if lesiones_activas > 0:
            obs.append(f'{lesiones_activas} lesión(es) activa(s)')

        alumnos_analisis.append({
            'alumno': alumno,
            'asistencias_90d': asistencias_90d,
            'total_asistencias': total_asistencias,
            'certificado_estado': cert_estado,
            'certificado_vigente': cert_vigente,
            'lesiones_activas': lesiones_activas,
            'ultima_promocion': ultima_promo,
            'meses_desde_promo': meses_desde_promo,
            'apto': apto,
            'observaciones': ', '.join(obs) if obs else 'Cumple todos los requisitos',
        })

    # Ordenar: aptos primero, luego por asistencias descendente
    alumnos_analisis.sort(
        key=lambda x: (not x['apto'], -x['asistencias_90d'])
    )

    total_aptos = sum(1 for a in alumnos_analisis if a['apto'])

    context = {
        'alumnos': alumnos_analisis,
        'total_aptos': total_aptos,
        'total_evaluados': len(alumnos_analisis),
        'min_asistencias': min_asistencias,
        'cinturon_filtro': cinturon_filtro,
        'cinturones': Student.Cinturon.choices,
        'hoy': hoy,
    }
    return render(request, 'reportes/reporte_aptos_examen.html', context)


@admin_required
def reporte_aptos_examen_excel(request):
    """Exporta el reporte de aptos para examen."""
    # Reutilizar la lógica de la vista (simplificada aquí)
    hoy = timezone.now().date()
    hace_90_dias = hoy - timedelta(days=90)
    min_asistencias = int(request.GET.get('min_asistencias', 24))

    alumnos_analisis = []
    for alumno in Student.objects.filter(estado='ACTIVO').select_related('certificado_medico'):
        asistencias_90d = Asistencia.objects.filter(
            alumno=alumno, fecha__gte=hace_90_dias, presente=True
        ).count()
        total = Asistencia.objects.filter(alumno=alumno, presente=True).count()

        cert_estado = 'Sin certificado'
        cert_vigente = False
        try:
            cert = alumno.certificado_medico
            if cert.fecha_vencimiento >= hoy:
                cert_estado = 'Vigente'
                cert_vigente = True
            else:
                cert_estado = 'Vencido'
        except CertificadoMedico.DoesNotExist:
            pass

        lesiones = alumno.lesiones.filter(
            estado__in=['ACTIVA', 'EN_RECUPERACION']
        ).count()

        apto = (
            asistencias_90d >= min_asistencias
            and cert_vigente
            and lesiones == 0
        )

        obs = []
        if asistencias_90d < min_asistencias:
            obs.append(f'Faltan {min_asistencias - asistencias_90d} asistencias')
        if not cert_vigente:
            obs.append('Certificado no vigente')
        if lesiones > 0:
            obs.append(f'{lesiones} lesión(es) activa(s)')

        alumnos_analisis.append({
            'alumno': alumno,
            'asistencias_90d': asistencias_90d,
            'total_asistencias': total,
            'certificado_estado': cert_estado,
            'apto': apto,
            'observaciones': ', '.join(obs) if obs else 'OK',
        })

    alumnos_analisis.sort(key=lambda x: (not x['apto'], -x['asistencias_90d']))

    buffer = exportar_aptos_examen_excel(alumnos_analisis, {})
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="aptos_examen_{hoy}.xlsx"'
    )
    return response


# ============================================================
# BÚSQUEDA GLOBAL (Ctrl+K)
# ============================================================
@instructor_required
def busqueda_global(request):
    """
    Endpoint HTMX para el widget de búsqueda global (Ctrl+K).
    Busca simultáneamente en: alumnos, eventos, pagos.
    """
    q = request.GET.get('q', '').strip()

    if len(q) < 2:
        return render(request, 'reportes/partials/_busqueda_vacia.html')

    # Alumnos
    alumnos = Student.objects.filter(
        Q(nombre__icontains=q)
        | Q(apellido__icontains=q)
        | Q(rut__icontains=q)
        | Q(email__icontains=q)
    ).order_by('apellido')[:8]

    # Eventos
    eventos = Evento.objects.filter(
        Q(nombre__icontains=q) | Q(lugar__icontains=q)
    ).order_by('-fecha')[:4]

    # Pagos (por número de recibo)
    pagos = Pago.objects.filter(
        Q(numero_recibo__icontains=q)
    ).select_related('alumno').order_by('-anio', '-mes')[:4]

    total = alumnos.count() + eventos.count() + pagos.count()

    return render(request, 'reportes/partials/_busqueda_resultados.html', {
        'q': q,
        'alumnos': alumnos,
        'eventos': eventos,
        'pagos': pagos,
        'total': total,
    })