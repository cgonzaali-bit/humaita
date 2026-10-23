#04102026 1806
# from django.db import models
# from alumnos.models import Student


# class Enfermedad(models.Model):
#     """Enfermedades registradas por alumno."""

#     GRAVEDAD = [
#         ('LEVE', 'Leve'),
#         ('MODERADA', 'Moderada'),
#         ('GRAVE', 'Grave'),
#     ]

#     alumno = models.ForeignKey(
#         Student, on_delete=models.CASCADE, related_name='enfermedades'
#     )
#     nombre = models.CharField(max_length=200)
#     descripcion = models.TextField(blank=True)
#     gravedad = models.CharField(max_length=20, choices=GRAVEDAD, default='LEVE')
#     tratamiento = models.TextField(blank=True)
#     activa = models.BooleanField(default=True)
#     fecha_registro = models.DateField(auto_now_add=True)

#     class Meta:
#         verbose_name = 'Enfermedad'
#         verbose_name_plural = 'Enfermedades'

#     def __str__(self):
#         return f"{self.alumno} - {self.nombre}"


# class Alergia(models.Model):
#     """Alergias del alumno."""

#     TIPOS = [
#         ('MEDICAMENTO', 'Medicamento'),
#         ('ALIMENTO', 'Alimento'),
#         ('AMBIENTAL', 'Ambiental'),
#         ('OTRA', 'Otra'),
#     ]

#     alumno = models.ForeignKey(
#         Student, on_delete=models.CASCADE, related_name='alergias'
#     )
#     tipo = models.CharField(max_length=20, choices=TIPOS)
#     descripcion = models.CharField(max_length=200)
#     severidad = models.CharField(
#         max_length=20,
#         choices=[('LEVE', 'Leve'), ('MODERADA', 'Moderada'), ('GRAVE', 'Grave')],
#         default='LEVE',
#     )
#     tratamiento = models.TextField(blank=True)

#     class Meta:
#         verbose_name = 'Alergia'
#         verbose_name_plural = 'Alergias'

#     def __str__(self):
#         return f"{self.alumno} - {self.descripcion}"


# class Lesion(models.Model):
#     """Lesiones previas o actuales."""

#     ESTADOS = [
#         ('ACTIVA', 'Activa'),
#         ('RECUPERADA', 'Recuperada'),
#         ('CRONICA', 'Crónica'),
#     ]

#     alumno = models.ForeignKey(
#         Student, on_delete=models.CASCADE, related_name='lesiones'
#     )
#     zona_cuerpo = models.CharField(max_length=100)
#     descripcion = models.TextField()
#     fecha_lesion = models.DateField()
#     estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVA')
#     observaciones = models.TextField(blank=True)

#     class Meta:
#         verbose_name = 'Lesión'
#         verbose_name_plural = 'Lesiones'
#         ordering = ['-fecha_lesion']

#     def __str__(self):
#         return f"{self.alumno} - {self.zona_cuerpo} ({self.estado})"


# class CertificadoMedico(models.Model):
#     """Certificado médico del alumno con fecha de vencimiento."""

#     alumno = models.OneToOneField(
#         Student, on_delete=models.CASCADE, related_name='certificado_medico'
#     )
#     archivo = models.FileField(upload_to='certificados/')
#     fecha_emision = models.DateField()
#     fecha_vencimiento = models.DateField()
#     medico = models.CharField(max_length=200, blank=True)
#     apto_para_competir = models.BooleanField(default=True)

#     class Meta:
#         verbose_name = 'Certificado médico'
#         verbose_name_plural = 'Certificados médicos'

#     def __str__(self):
#         return f"Certificado de {self.alumno} - vence {self.fecha_vencimiento}"


# class ContactoEmergencia(models.Model):
#     """Contacto de emergencia del alumno."""

#     alumno = models.OneToOneField(
#         Student, on_delete=models.CASCADE, related_name='contacto_emergencia'
#     )
#     nombre = models.CharField(max_length=200)
#     telefono = models.CharField(max_length=20)
#     parentesco = models.CharField(max_length=50)
#     notas = models.TextField(blank=True)

#     class Meta:
#         verbose_name = 'Contacto de emergencia'
#         verbose_name_plural = 'Contactos de emergencia'

#     def __str__(self):
#         return f"{self.alumno} - {self.nombre} ({self.parentesco})"



from django.db import models
from django.utils import timezone
from datetime import timedelta

from alumnos.models import Student


# ============================================================
# ENFERMEDAD
# ============================================================
class Enfermedad(models.Model):
    GRAVEDAD = [
        ('LEVE', 'Leve'),
        ('MODERADA', 'Moderada'),
        ('GRAVE', 'Grave'),
    ]

    alumno = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='enfermedades'
    )
    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    gravedad = models.CharField(
        max_length=20, choices=GRAVEDAD, default='LEVE', verbose_name='Gravedad'
    )
    tratamiento = models.TextField(blank=True, verbose_name='Tratamiento')
    medicamentos = models.TextField(
        blank=True,
        verbose_name='Medicamentos',
        help_text='Medicamentos que toma regularmente'
    )
    activa = models.BooleanField(default=True, verbose_name='Activa')
    fecha_registro = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Enfermedad'
        verbose_name_plural = 'Enfermedades'
        ordering = ['-gravedad', '-fecha_registro']

    def __str__(self):
        return f"{self.alumno} - {self.nombre}"

    @property
    def es_critica(self):
        return self.gravedad == 'GRAVE' and self.activa


# ============================================================
# ALERGIA
# ============================================================
class Alergia(models.Model):
    TIPOS = [
        ('MEDICAMENTO', 'Medicamento'),
        ('ALIMENTO', 'Alimento'),
        ('AMBIENTAL', 'Ambiental'),
        ('CONTACTO', 'Contacto / Piel'),
        ('OTRA', 'Otra'),
    ]
    SEVERIDAD = [
        ('LEVE', 'Leve'),
        ('MODERADA', 'Moderada'),
        ('GRAVE', 'Grave (anafilaxia)'),
    ]

    alumno = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='alergias'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS, verbose_name='Tipo')
    descripcion = models.CharField(max_length=200, verbose_name='Descripción')
    severidad = models.CharField(
        max_length=20, choices=SEVERIDAD, default='LEVE', verbose_name='Severidad'
    )
    tratamiento = models.TextField(blank=True, verbose_name='Tratamiento')
    requiere_epipen = models.BooleanField(
        default=False, verbose_name='¿Requiere EpiPen?'
    )
    activa = models.BooleanField(default=True, verbose_name='Activa')

    class Meta:
        verbose_name = 'Alergia'
        verbose_name_plural = 'Alergias'
        ordering = ['-severidad', 'tipo']

    def __str__(self):
        return f"{self.alumno} - {self.descripcion}"

    @property
    def es_critica(self):
        return self.severidad == 'GRAVE' and self.activa


# ============================================================
# LESIÓN
# ============================================================
class Lesion(models.Model):
    ESTADOS = [
        ('ACTIVA', 'Activa'),
        ('EN_RECUPERACION', 'En recuperación'),
        ('CRONICA', 'Crónica'),
        ('RECUPERADA', 'Recuperada'),
    ]
    ZONAS = [
        ('CUELLO', 'Cuello'),
        ('HOMBRO', 'Hombro'),
        ('CODO', 'Codo'),
        ('MUNECA', 'Muñeca / Mano'),
        ('ESPALDA', 'Espalda'),
        ('LUMBAR', 'Zona lumbar'),
        ('CADERA', 'Cadera / Ingle'),
        ('RODILLA', 'Rodilla'),
        ('TOBILLO', 'Tobillo / Pie'),
        ('COSTILLAS', 'Costillas'),
        ('OTRA', 'Otra'),
    ]

    alumno = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='lesiones'
    )
    zona_cuerpo = models.CharField(
        max_length=20, choices=ZONAS, verbose_name='Zona del cuerpo'
    )
    descripcion = models.TextField(verbose_name='Descripción')
    fecha_lesion = models.DateField(verbose_name='Fecha de lesión')
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default='ACTIVA', verbose_name='Estado'
    )
    tratamiento = models.TextField(blank=True, verbose_name='Tratamiento')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')

    class Meta:
        verbose_name = 'Lesión'
        verbose_name_plural = 'Lesiones'
        ordering = ['-fecha_lesion']

    def __str__(self):
        return f"{self.alumno} - {self.get_zona_cuerpo_display()} ({self.get_estado_display()})"

    @property
    def impide_entrenar(self):
        return self.estado in ('ACTIVA', 'EN_RECUPERACION')

    @property
    def dias_desde_lesion(self):
        return (timezone.now().date() - self.fecha_lesion).days


# ============================================================
# CERTIFICADO MÉDICO
# ============================================================
class CertificadoMedicoQuerySet(models.QuerySet):
    def vigentes(self):
        return self.filter(fecha_vencimiento__gte=timezone.now().date())

    def vencidos(self):
        return self.filter(fecha_vencimiento__lt=timezone.now().date())

    def por_vencer(self, dias=30):
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=dias)
        return self.filter(fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=limite)


class CertificadoMedico(models.Model):
    alumno = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name='certificado_medico'
    )
    archivo = models.FileField(
        upload_to='certificados/%Y/%m/', verbose_name='Archivo'
    )
    fecha_emision = models.DateField(verbose_name='Fecha de emisión')
    fecha_vencimiento = models.DateField(verbose_name='Fecha de vencimiento')
    medico = models.CharField(max_length=200, blank=True, verbose_name='Médico')
    numero_registro = models.CharField(
        max_length=100, blank=True, verbose_name='N° de registro'
    )
    apto_para_competir = models.BooleanField(
        default=True, verbose_name='¿Apto para competir?'
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')

    objects = CertificadoMedicoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Certificado médico'
        verbose_name_plural = 'Certificados médicos'

    def __str__(self):
        return f"Certificado de {self.alumno} - vence {self.fecha_vencimiento}"

    @property
    def esta_vigente(self):
        return self.fecha_vencimiento >= timezone.now().date()

    @property
    def dias_para_vencer(self):
        return (self.fecha_vencimiento - timezone.now().date()).days

    @property
    def estado_alerta(self):
        """Retorna: 'VENCIDO', 'CRITICO', 'PROXIMO' o 'OK'."""
        dias = self.dias_para_vencer
        if dias < 0:
            return 'VENCIDO'
        if dias <= 15:
            return 'CRITICO'
        if dias <= 30:
            return 'PROXIMO'
        return 'OK'


# ============================================================
# CONTACTO DE EMERGENCIA
# ============================================================
class ContactoEmergencia(models.Model):
    alumno = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name='contacto_emergencia'
    )
    nombre = models.CharField(max_length=200, verbose_name='Nombre completo')
    telefono = models.CharField(max_length=20, verbose_name='Teléfono')
    telefono_alternativo = models.CharField(
        max_length=20, blank=True, verbose_name='Teléfono alternativo'
    )
    parentesco = models.CharField(max_length=50, verbose_name='Parentesco')
    es_tutor_legal = models.BooleanField(
        default=False, verbose_name='¿Es tutor legal?'
    )
    notas = models.TextField(blank=True, verbose_name='Notas')

    class Meta:
        verbose_name = 'Contacto de emergencia'
        verbose_name_plural = 'Contactos de emergencia'

    def __str__(self):
        return f"{self.alumno} - {self.nombre} ({self.parentesco})"