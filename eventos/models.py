from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

from alumnos.models import Student


# ============================================================
# EVENTO
# ============================================================
class EventoQuerySet(models.QuerySet):
    def proximos(self):
        return self.filter(
            activo=True, fecha__gte=timezone.now()
        ).order_by('fecha')

    def pasados(self):
        return self.filter(fecha__lt=timezone.now()).order_by('-fecha')

    def del_tipo(self, tipo):
        return self.filter(tipo=tipo)


class Evento(models.Model):
    """Evento especial: seminario, competencia, examen, exhibición."""

    class Tipo(models.TextChoices):
        SEMINARIO = 'SEMINARIO', 'Seminario'
        MASTERCLASS = 'MASTERCLASS', 'Masterclass'
        COMPETENCIA = 'COMPETENCIA', 'Competencia'
        EXAMEN = 'EXAMEN', 'Examen de cinturón'
        EXHIBICION = 'EXHIBICION', 'Exhibición'
        OTRO = 'OTRO', 'Otro'

    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', 'Borrador'
        ABIERTO = 'ABIERTO', 'Inscripciones abiertas'
        CERRADO = 'CERRADO', 'Inscripciones cerradas'
        EN_CURSO = 'EN_CURSO', 'En curso'
        FINALIZADO = 'FINALIZADO', 'Finalizado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    tipo = models.CharField(max_length=20, choices=Tipo.choices, verbose_name='Tipo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    fecha = models.DateTimeField(verbose_name='Fecha y hora')
    fecha_fin = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha de fin (opcional)'
    )
    lugar = models.CharField(max_length=200, blank=True, verbose_name='Lugar')

    costo = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Costo',
    )
    cupo_maximo = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Cupo máximo'
    )

    estado = models.CharField(
        max_length=20, choices=Estado.choices,
        default=Estado.BORRADOR, verbose_name='Estado'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')

    # Para exámenes de cinturón
    cinturon_objetivo = models.CharField(
        max_length=20, blank=True,
        choices=[
            ('BLANCO', 'Blanco'), ('AZUL', 'Azul'), ('MORADO', 'Morado'),
            ('MARRON', 'Marrón'), ('NEGRO', 'Negro'),
        ],
        verbose_name='Cinturón objetivo',
        help_text='Solo para exámenes de cinturón',
    )

    creado_por = models.ForeignKey(
        'usuarios.User', on_delete=models.SET_NULL, null=True,
        related_name='eventos_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True, null=True, blank=True)

    objects = EventoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['estado', 'fecha']),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()}) - {self.fecha.date()}"

    # ===== Propiedades =====
    @property
    def es_pasado(self):
        return self.fecha < timezone.now()

    @property
    def es_futuro(self):
        return self.fecha >= timezone.now()

    @property
    def inscripciones_abiertas(self):
        return self.estado == self.Estado.ABIERTO and self.es_futuro

    @property
    def cupos_disponibles(self):
        if not self.cupo_maximo:
            return None
        return self.cupo_maximo - self.inscripciones.count()

    @property
    def esta_lleno(self):
        if not self.cupo_maximo:
            return False
        return self.inscripciones.count() >= self.cupo_maximo

    @property
    def total_recaudado(self):
        from django.db.models import Sum
        return self.inscripciones.filter(
            estado_pago='PAGADO'
        ).aggregate(t=Sum('monto_pagado'))['t'] or Decimal('0')

    @property
    def total_inscritos(self):
        return self.inscripciones.count()


# ============================================================
# INSCRIPCIÓN A EVENTO
# ============================================================
class InscripcionEvento(models.Model):
    """Inscripción de un alumno a un evento."""

    class EstadoPago(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADO = 'PAGADO', 'Pagado'
        EXIMIDO = 'EXIMIDO', 'Eximido'

    class Resultado(models.TextChoices):
        ORO = 'ORO', '🥇 Oro'
        PLATA = 'PLATA', '🥈 Plata'
        BRONCE = 'BRONCE', '🥉 Bronce'
        PARTICIPACION = 'PARTICIPACION', 'Participación'
        APROBADO = 'APROBADO', 'Aprobado'
        REPROBADO = 'REPROBADO', 'Reprobado'

    evento = models.ForeignKey(
        Evento, on_delete=models.CASCADE, related_name='inscripciones'
    )
    alumno = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='inscripciones_eventos'
    )
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    estado_pago = models.CharField(
        max_length=20, choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE, verbose_name='Estado del pago'
    )
    monto_pagado = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'),
        verbose_name='Monto pagado'
    )
    fecha_pago = models.DateField(null=True, blank=True, verbose_name='Fecha de pago')
    metodo_pago = models.CharField(max_length=20, blank=True, verbose_name='Método de pago')

    resultado = models.CharField(
        max_length=20, choices=Resultado.choices, blank=True,
        verbose_name='Resultado'
    )
    posicion = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name='Posición'
    )
    categoria_competencia = models.CharField(
        max_length=100, blank=True, verbose_name='Categoría de competencia'
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')

    class Meta:
        verbose_name = 'Inscripción a evento'
        verbose_name_plural = 'Inscripciones a eventos'
        unique_together = ['evento', 'alumno']
        ordering = ['-fecha_inscripcion']

    def __str__(self):
        return f"{self.alumno} → {self.evento.nombre}"

    @property
    def tiene_resultado(self):
        return bool(self.resultado)


# ============================================================
# GALERÍA DE FOTOS POR EVENTO
# ============================================================
class FotoEvento(models.Model):
    """Fotos asociadas a un evento (galería)."""

    evento = models.ForeignKey(
        Evento, on_delete=models.CASCADE, related_name='fotos'
    )
    imagen = models.ImageField(upload_to='eventos/%Y/%m/')
    titulo = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)
    subida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto de evento'
        verbose_name_plural = 'Fotos de eventos'
        ordering = ['-subida_en']

    def __str__(self):
        return f"{self.evento.nombre} - {self.titulo or self.pk}"