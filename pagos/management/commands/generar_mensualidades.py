from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal

from alumnos.models import Student
from pagos.models import PlanPago, Pago


class Command(BaseCommand):
    help = 'Genera mensualidades pendientes para el mes actual o el indicado'

    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, help='Mes (1-12)')
        parser.add_argument('--anio', type=int, help='Año')

    def handle(self, *args, **options):
        hoy = timezone.now().date()
        mes = options['mes'] or hoy.month
        anio = options['anio'] or hoy.year

        creados = 0
        for alumno in Student.objects.filter(estado='ACTIVO'):
            if Pago.objects.filter(alumno=alumno, mes=mes, anio=anio).exists():
                continue
            plan = PlanPago.objects.filter(
                activo=True, tipo_alumno=alumno.categoria
            ).first() or PlanPago.objects.filter(
                activo=True, tipo_alumno='TODOS'
            ).first()
            if not plan:
                continue
            Pago.objects.create(
                alumno=alumno, plan=plan, mes=mes, anio=anio,
                monto=plan.monto, estado=Pago.Estado.PENDIENTE,
            )
            creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Generadas {creados} mensualidades para {mes:02d}/{anio}'
        ))