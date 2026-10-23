#14102026 1804
from django.db import models
from django.conf import settings


class Student(models.Model):
    """Alumno de la academia."""

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        INACTIVO = 'INACTIVO', 'Inactivo'
        CONGELADO = 'CONGELADO', 'Congelado (lesión/viaje)'
        EGRESADO = 'EGRESADO', 'Egresado'

    class Cinturon(models.TextChoices):
        BLANCO = 'BLANCO', 'Blanco'
        AZUL = 'AZUL', 'Azul'
        MORADO = 'MORADO', 'Morado'
        MARRON = 'MARRON', 'Marrón'
        NEGRO = 'NEGRO', 'Negro'

    class Categoria(models.TextChoices):
        INFANTIL = 'INFANTIL', 'Infantil (4-12)'
        JUVENIL = 'JUVENIL', 'Juvenil (13-17)'
        ADULTO = 'ADULTO', 'Adulto (18-35)'
        MASTER = 'MASTER', 'Master (36+)'

    # Datos personales
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    rut = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    foto_perfil = models.ImageField(upload_to='alumnos/perfiles/', blank=True, null=True)

    # Datos de academia
    cinturon_actual = models.CharField(
        max_length=20, choices=Cinturon.choices, default=Cinturon.BLANCO
    )
    grados_cinturon = models.PositiveSmallIntegerField(default=0)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    fecha_inicio = models.DateField(auto_now_add=True)

    # Tutor (obligatorio si es menor)
    tutor_nombre = models.CharField(max_length=200, blank=True)
    tutor_telefono = models.CharField(max_length=20, blank=True)
    tutor_parentesco = models.CharField(max_length=50, blank=True)

    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"


class BeltHistory(models.Model):
    """Historial de promociones de cinturón."""

    alumno = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='historial_cinturones'
    )
    cinturon_anterior = models.CharField(max_length=20, choices=Student.Cinturon.choices)
    cinturon_nuevo = models.CharField(max_length=20, choices=Student.Cinturon.choices)
    grados = models.PositiveSmallIntegerField(default=0)
    fecha_promocion = models.DateField()
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Promoción de cinturón'
        verbose_name_plural = 'Historial de cinturones'
        ordering = ['-fecha_promocion']

    def __str__(self):
        return f"{self.alumno} → {self.get_cinturon_nuevo_display()} ({self.fecha_promocion})"
