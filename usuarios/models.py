from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class User(AbstractUser):
    """
    Modelo de usuario personalizado para ArmyLock.
    Incluye roles, datos de contacto y perfil completo de instructor.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Dueño / Super Admin'
        ADMIN = 'ADMIN', 'Administrador'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
        ALUMNO = 'ALUMNO', 'Alumno'

    class Cinturon(models.TextChoices):
        BLANCO = 'BLANCO', 'Blanco'
        AZUL = 'AZUL', 'Azul'
        MORADO = 'MORADO', 'Morado'
        MARRON = 'MARRON', 'Marrón'
        NEGRO = 'NEGRO', 'Negro'

    # ===== Campos base =====
    role = models.CharField(
        max_length=20, choices=Role.choices,
        default=Role.ALUMNO, verbose_name='Rol',
    )
    telefono = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    foto_perfil = models.ImageField(
        upload_to='staff/perfiles/', blank=True, null=True,
        verbose_name='Foto de perfil',
    )
    ultimo_acceso = models.DateTimeField(
        null=True, blank=True, verbose_name='Último acceso',
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')

    # ===== Cinturón =====
    cinturon_actual = models.CharField(
        max_length=20, choices=Cinturon.choices,
        default=Cinturon.BLANCO, verbose_name='Cinturón actual',
    )
    grados_cinturon = models.PositiveSmallIntegerField(
        default=0, verbose_name='Grados (0-4)',
    )

    # ===== Perfil de instructor =====
    fecha_inicio_ensenanza = models.DateField(
        null=True, blank=True, verbose_name='Inicio como instructor',
        help_text='Fecha en que comenzó a enseñar en la academia',
    )
    biografia = models.TextField(
        blank=True, verbose_name='Biografía',
        help_text='Breve reseña deportiva del instructor',
    )
    especialidades = models.CharField(
        max_length=300, blank=True, verbose_name='Especialidades',
        help_text='Ej: Guardia, finalizaciones, wrestling, MMA',
    )
    certificaciones = models.TextField(
        blank=True, verbose_name='Certificaciones',
        help_text='Certificaciones oficiales, cursos, etc.',
    )
    profesor_mentor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='alumnos_formados',
        limit_choices_to={'role__in': ['SUPER_ADMIN', 'ADMIN', 'INSTRUCTOR']},
        verbose_name='Profesor mentor',
        help_text='Quién formó / certificó a este instructor',
    )
    horario_disponible = models.CharField(
        max_length=200, blank=True, verbose_name='Disponibilidad',
        help_text='Ej: L-M-V tardes, Sábados mañana',
    )

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    # ===== Permisos =====
    @property
    def es_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def es_admin(self):
        return self.role in (self.Role.SUPER_ADMIN, self.Role.ADMIN)

    @property
    def es_instructor(self):
        return self.role in (
            self.Role.SUPER_ADMIN, self.Role.ADMIN, self.Role.INSTRUCTOR
        )

    # ===== Nivel de instructor =====
    @property
    def nivel_instructor(self):
        """
        Retorna el nivel de instructor según el cinturón.
        Retorna None si no puede enseñar.
        """
        if self.role == self.Role.ALUMNO:
            return None
        niveles = {
            'BLANCO': None,
            'AZUL': 'MONITOR',
            'MORADO': 'INSTRUCTOR',
            'MARRON': 'INSTRUCTOR_AVANZADO',
            'NEGRO': 'PROFESOR',
        }
        return niveles.get(self.cinturon_actual)

    @property
    def nivel_instructor_display(self):
        """Nombre legible del nivel."""
        niveles = {
            'MONITOR': 'Monitor',
            'INSTRUCTOR': 'Instructor',
            'INSTRUCTOR_AVANZADO': 'Instructor Avanzado',
            'PROFESOR': 'Profesor / Maestro',
        }
        return niveles.get(self.nivel_instructor, 'Sin nivel')

    @property
    def puede_ensenar(self):
        """Solo azul en adelante puede enseñar."""
        return self.nivel_instructor is not None

    @property
    def puede_graduar(self):
        """Solo cinturón negro puede otorgar cinturones."""
        return self.cinturon_actual == 'NEGRO' and self.es_instructor

    @property
    def anios_ensenando(self):
        """Años desde que comenzó a enseñar."""
        if not self.fecha_inicio_ensenanza:
            return None
        delta = timezone.now().date() - self.fecha_inicio_ensenanza
        return round(delta.days / 365, 1)

    # ===== Validación =====
    def clean(self):
        super().clean()
        # Si va a ser instructor, debe tener cinturón azul o superior
        if self.role == self.Role.INSTRUCTOR:
            if self.cinturon_actual == self.Cinturon.BLANCO:
                raise ValidationError({
                    'cinturon_actual': (
                        'Para ser instructor se requiere cinturón azul o superior.'
                    )
                })

    def save(self, *args, **kwargs):
        # Auto-degradar a ALUMNO si no puede enseñar
        if self.role == self.Role.INSTRUCTOR and not self.puede_ensenar:
            self.role = self.Role.ALUMNO
        super().save(*args, **kwargs)


# ============================================================
# LOG DE AUDITORÍA
# ============================================================
class AuditLog(models.Model):
    """Registro de acciones importantes realizadas por usuarios."""

    ACCIONES = [
        ('CREAR', 'Creación'),
        ('EDITAR', 'Edición'),
        ('ELIMINAR', 'Eliminación'),
        ('LOGIN', 'Inicio de sesión'),
        ('LOGOUT', 'Cierre de sesión'),
        ('PAGO', 'Registro de pago'),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='auditoria', verbose_name='Usuario',
    )
    accion = models.CharField(max_length=20, choices=ACCIONES, verbose_name='Acción')
    modelo_afectado = models.CharField(max_length=100, blank=True)
    objeto_id = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de auditoría'
        verbose_name_plural = 'Logs de auditoría'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.usuario} - {self.accion}"