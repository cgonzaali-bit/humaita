from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Student


@receiver(post_save, sender=Student)
def normalizar_datos_alumno(sender, instance, created, **kwargs):
    """
    Al crear un alumno, si su RUT no está en mayúsculas,
    lo normalizamos sin disparar otra save() recursiva.
    """
    if created and instance.rut and instance.rut != instance.rut.upper():
        Student.objects.filter(pk=instance.pk).update(rut=instance.rut.upper())