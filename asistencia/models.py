from django.db import models
from django.utils import timezone
from django.conf import settings

from alumnos.models import Student


# ============================================================
# CLASE
# ============================================================
class ClaseQuerySet(models.QuerySet):
    def activas(self):
        return self.filter(activo=True)

    def del_dia(self, dia):
        return self.filter(dia_semana=dia, activo=True)


class Clase(models.Model):
    """Clase programada en el horario del dojo."""

    class DiaSemana(models.IntegerChoices):
        LUNES = 0, 'Lunes'
        MARTES = 1, 'Martes'
        MIERCOLES = 2, 'Miércoles'
        JUEVES = 3, 'Jueves'
        VIERNES = 4, 'Viernes'
        SABADO = 5, 'Sábado'
        DOMINGO = 6, 'Domingo'

    class Categoria(models.TextChoices):
        INFANTIL = 'INFANTIL', 'Infantil'
        JUVENIL = 'JUVENIL', 'Juvenil'
        ADULTO = 'ADULTO', 'Adulto'
        TODOS = 'TODOS', 'Todos'
        COMPETIDORES = 'COMPETIDORES', 'Competidores'
        PRINCIPIANTES = 'PRINCIPIANTES', 'Principiantes'

    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    dia_semana = models.PositiveSmallIntegerField(
        choices=DiaSemana.choices, verbose_name='Día'
    )
    hora_inicio = models.TimeField(verbose_name='Hora de inicio')
    hora_fin = models.TimeField(verbose_name='Hora de fin')
    categoria = models.CharField(
        max_length=20, choices=Categoria.choices,
        default=Categoria.TODOS, verbose_name='Categoría'
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Instructor',
        related_name='clases_impartidas',
    )
    cupo_maximo = models.PositiveIntegerField(
        default=20, null=True, blank=True, verbose_name='Cupo máximo'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Clase'
        verbose_name_plural = 'Clases'
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        return f"{self.nombre} - {self.get_dia_semana_display()} {self.hora_inicio.strftime('%H:%M')}"


# ============================================================
# ASISTENCIA
# ============================================================
class AsistenciaQuerySet(models.QuerySet):
    def del_dia(self, fecha):
        return self.filter(fecha=fecha)

    def del_alumno(self, alumno):
        return self.filter(alumno=alumno)

    def presentes(self):
        return self.filter(presente=True)


class Asistencia(models.Model):
    """Registro de asistencia de un alumno a una clase."""

    alumno = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='asistencias'
    )
    clase = models.ForeignKey(
        Clase, on_delete=models.CASCADE, related_name='asistencias'
    )
    fecha = models.DateField(verbose_name='Fecha')

    presente = models.BooleanField(default=True, verbose_name='Presente')
    hora_registro = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='Hora de registro')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='asistencias_registradas',
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')

    objects = AsistenciaQuerySet.as_manager()

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        unique_together = ['alumno', 'clase', 'fecha']
        ordering = ['-fecha', '-hora_registro']
        indexes = [
            models.Index(fields=['fecha', 'clase']),
        ]

    def __str__(self):
        estado = 'Presente' if self.presente else 'Ausente'
        return f"{self.alumno} - {self.fecha} - {self.clase.nombre} - {estado}"