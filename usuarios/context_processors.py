from django.utils import timezone
from datetime import timedelta


def alertas_globales(request):
    """
    Context processor que inyecta contadores de alertas en todas las templates.
    Se ejecuta en cada request — mantener las queries ligeras y condicionadas.
    """
    if not request.user.is_authenticated:
        return {}

    # Solo admin/instructor necesita ver alertas
    if not getattr(request.user, 'es_instructor', False):
        return {'alertas_total': 0}

    hoy = timezone.now().date()
    hace_30_dias = hoy + timedelta(days=30)
    mes_actual = hoy.month
    anio_actual = hoy.year

    # Importar aquí para evitar circular imports
    from salud.models import CertificadoMedico
    from pagos.models import Pago

    # 1. Certificados vencidos o por vencer (15 días)
    certificados_alerta = CertificadoMedico.objects.filter(
        fecha_vencimiento__lte=hace_30_dias
    ).count()

    # 2. Pagos atrasados del mes actual
    pagos_atrasados = Pago.objects.filter(
        estado__in=['PENDIENTE', 'ATRASADO'],
        fecha_vencimiento__lt=hoy,
    ).count()

    # 3. Total
    total = certificados_alerta + pagos_atrasados

    return {
        'alertas_salud': certificados_alerta,
        'alertas_pagos': pagos_atrasados,
        'alertas_total': total,
    }