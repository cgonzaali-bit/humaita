#14102026 1808
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

from alumnos.models import Student


# ============================================================
# PLAN DE PAGO
# ============================================================
class PlanPago(models.Model):
    """Planes de pago configurados por la academia."""

    class TipoAlumno(models.TextChoices):
        INFANTIL = 'INFANTIL', 'Infantil (4-12)'
        JUVENIL = 'JUVENIL', 'Juvenil (13-17)'
        ADULTO = 'ADULTO', 'Adulto (18-35)'
        MASTER = 'MASTER', 'Master (36+)'
        FAMILIAR = 'FAMILIAR', 'Plan familiar'
        TODOS = 'TODOS', 'Todos'

    class Frecuencia(models.TextChoices):
        LIBRE = '0', 'Ilimitado (todos los días)'
        DOS_X = '2', '2 veces por semana'
        TRES_X = '3', '3 veces por semana'
        CUATRO_X = '4', '4 veces por semana'

    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    monto = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Monto mensual',
    )
    tipo_alumno = models.CharField(
        max_length=20, choices=TipoAlumno.choices,
        default=TipoAlumno.TODOS, verbose_name='Tipo de alumno',
    )
    frecuencia = models.CharField(
        max_length=2, choices=Frecuencia.choices,
        default=Frecuencia.LIBRE, verbose_name='Frecuencia semanal',
    )
    es_familiar = models.BooleanField(
        default=False, verbose_name='¿Es plan familiar?',
        help_text='Aplica descuento por inscribir varios hermanos',
    )
    descuento_familiar_porcentaje = models.PositiveSmallIntegerField(
        default=10, verbose_name='Descuento familiar (%)',
        help_text='Solo aplica si es plan familiar',
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    creado_en = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Plan de pago'
        verbose_name_plural = 'Planes de pago'
        ordering = ['tipo_alumno', 'monto']

    def __str__(self):
        return f"{self.nombre} - ${self.monto:,.0f}"


# ============================================================
# PAGO
# ============================================================
class PagoQuerySet(models.QuerySet):
    def del_periodo(self, mes, anio):
        return self.filter(mes=mes, anio=anio)

    def del_anio(self, anio):
        return self.filter(anio=anio)

    def pagados(self):
        return self.filter(estado='PAGADO')

    def pendientes(self):
        return self.filter(estado__in=['PENDIENTE', 'ATRASADO'])

    def atrasados(self):
        hoy = timezone.now().date()
        return self.filter(
            estado__in=['PENDIENTE', 'ATRASADO'],
            fecha_vencimiento__lt=hoy,
        )

    def total_recaudado(self):
        from django.db.models import Sum
        return self.pagados().aggregate(
            total=Sum('monto_final')
        )['total'] or Decimal('0')


class Pago(models.Model):
    """Pago de mensualidad de un alumno."""

    class Estado(models.TextChoices):
        PAGADO = 'PAGADO', 'Pagado'
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ATRASADO = 'ATRASADO', 'Atrasado'
        EXIMIDO = 'EXIMIDO', 'Eximido'
        BECA = 'BECA', 'Beca'

    class Metodo(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'
        TARJETA_DEBITO = 'TARJETA_DEBITO', 'Tarjeta de débito'
        TARJETA_CREDITO = 'TARJETA_CREDITO', 'Tarjeta de crédito'
        MERCADOPAGO = 'MERCADOPAGO', 'MercadoPago'
        OTRO = 'OTRO', 'Otro'

    # Relaciones
    alumno = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name='pagos'
    )
    plan = models.ForeignKey(
        PlanPago, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pagos', verbose_name='Plan',
    )

    # Período
    mes = models.PositiveSmallIntegerField(verbose_name='Mes')
    anio = models.PositiveSmallIntegerField(verbose_name='Año')

    # Montos
    monto = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Monto base',
    )
    descuento = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Descuento',
    )
    monto_final = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Monto final',
    )

    # Estado
    estado = models.CharField(
        max_length=20, choices=Estado.choices,
        default=Estado.PENDIENTE, verbose_name='Estado',
    )

    # Pago
    metodo_pago = models.CharField(
        max_length=20, choices=Metodo.choices, blank=True,
        verbose_name='Método de pago',
    )
    fecha_pago = models.DateField(null=True, blank=True, verbose_name='Fecha de pago')
    fecha_vencimiento = models.DateField(
        null=True, blank=True, verbose_name='Fecha de vencimiento',
    )
    referencia = models.CharField(
        max_length=100, blank=True, verbose_name='Referencia',
        help_text='N° de transferencia, voucher, etc.',
    )

    # Recibo
    numero_recibo = models.CharField(
        max_length=20, unique=True, blank=True, null=True,
        verbose_name='N° de recibo',
    )

    # Meta
    registrado_por = models.ForeignKey(
        'usuarios.User', on_delete=models.SET_NULL, null=True,
        related_name='pagos_registrados', verbose_name='Registrado por',
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    creado_en = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = PagoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-anio', '-mes', 'alumno__apellido']
        unique_together = ['alumno', 'mes', 'anio']
        indexes = [
            models.Index(fields=['anio', 'mes']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_vencimiento']),
        ]

    def __str__(self):
        return f"{self.alumno} - {self.mes:02d}/{self.anio} - ${self.monto_final}"

    # ===== Cálculos =====
    def save(self, *args, **kwargs):
        # Calcular monto final
        self.monto_final = (self.monto or 0) - (self.descuento or 0)
        if self.monto_final < 0:
            self.monto_final = Decimal('0')

        # Asignar fecha de vencimiento si no existe
        if not self.fecha_vencimiento:
            from django.conf import settings
            dia = getattr(settings, 'DIA_VENCIMIENTO_MENSUALIDAD', 5)
            try:
                self.fecha_vencimiento = timezone.datetime(
                    self.anio, self.mes, dia
                ).date()
            except ValueError:
                # Mes con menos días (ej: feb=28)
                self.fecha_vencimiento = timezone.datetime(
                    self.anio, self.mes, 28
                ).date()

        # Generar número de recibo al pasar a PAGADO
        if self.estado == self.Estado.PAGADO and not self.numero_recibo:
            self.numero_recibo = self._generar_numero_recibo()

        super().save(*args, **kwargs)

    def _generar_numero_recibo(self):
        """Genera un número secuencial: AL-2025-0001."""
        from django.conf import settings
        prefijo = getattr(settings, 'PREFIJO_RECIBO', 'AL')
        correlativo = Pago.objects.filter(
            anio=self.anio, numero_recibo__isnull=False
        ).count() + 1
        return f"{prefijo}-{self.anio}-{correlativo:04d}"

    # ===== Propiedades =====
    @property
    def periodo_display(self):
        meses = [
            '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
        return f"{meses[self.mes]} {self.anio}"

    @property
    def esta_pagado(self):
        return self.estado == self.Estado.PAGADO

    @property
    def esta_vencido(self):
        if self.esta_pagado or not self.fecha_vencimiento:
            return False
        return self.fecha_vencimiento < timezone.now().date()

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.now().date()).days

    @property
    def dias_atraso(self):
        if not self.esta_vencido:
            return 0
        return abs(self.dias_para_vencer)

    @property
    def estado_alerta(self):
        """VENCIDO / CRITICO / PROXIMO / OK / PAGADO."""
        if self.esta_pagado:
            return 'PAGADO'
        if self.estado in ('EXIMIDO', 'BECA'):
            return 'OK'
        dias = self.dias_para_vencer
        if dias is None:
            return 'OK'
        if dias < 0:
            return 'VENCIDO'
        if dias <= 3:
            return 'CRITICO'
        if dias <= 10:
            return 'PROXIMO'
        return 'OK'


# ============================================================
# DESCUENTO / PROMOCIÓN
# ============================================================
class Promocion(models.Model):
    """Promociones aplicables al pago de mensualidad."""

    TIPOS = [
        ('PORCENTAJE', 'Porcentaje'),
        ('MONTO_FIJO', 'Monto fijo'),
    ]

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()} - {self.valor})"

    @property
    def vigente(self):
        hoy = timezone.now().date()
        return self.activa and self.fecha_inicio <= hoy <= self.fecha_fin