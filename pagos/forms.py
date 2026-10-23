from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from alumnos.models import Student
from .models import PlanPago, Pago, Promocion


BASE_INPUT = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition'
BASE_TEXTAREA = BASE_INPUT + ' resize-y'
BASE_CHECKBOX = 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'

MESES = [
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
]


class PlanPagoForm(forms.ModelForm):
    class Meta:
        model = PlanPago
        fields = ['nombre', 'descripcion', 'monto', 'tipo_alumno',
                  'frecuencia', 'es_familiar', 'descuento_familiar_porcentaje',
                  'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': BASE_INPUT, 'placeholder': 'Ej: Adulto ilimitado',
                'autofocus': True,
            }),
            'descripcion': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
            'monto': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'step': '100', 'min': '0',
                'placeholder': '35000',
            }),
            'tipo_alumno': forms.Select(attrs={'class': BASE_INPUT}),
            'frecuencia': forms.Select(attrs={'class': BASE_INPUT}),
            'es_familiar': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
            'descuento_familiar_porcentaje': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'min': 0, 'max': 100,
            }),
            'activo': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        }


class PagoForm(forms.ModelForm):
    """Formulario de registro/edición de pago."""

    class Meta:
        model = Pago
        fields = ['alumno', 'plan', 'mes', 'anio', 'monto', 'descuento',
                  'estado', 'metodo_pago', 'fecha_pago', 'referencia',
                  'observaciones']
        widgets = {
            'alumno': forms.Select(attrs={'class': BASE_INPUT, 'id': 'id_alumno'}),
            'plan': forms.Select(attrs={'class': BASE_INPUT, 'id': 'id_plan'}),
            'mes': forms.Select(choices=MESES, attrs={'class': BASE_INPUT}),
            'anio': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'min': 2020, 'max': 2100,
            }),
            'monto': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'step': '100', 'min': '0',
                'id': 'id_monto',
            }),
            'descuento': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'step': '100', 'min': '0',
                'id': 'id_descuento',
            }),
            'estado': forms.Select(attrs={'class': BASE_INPUT, 'id': 'id_estado'}),
            'metodo_pago': forms.Select(attrs={'class': BASE_INPUT}),
            'fecha_pago': forms.DateInput(attrs={
                'class': BASE_INPUT, 'type': 'date',
            }),
            'referencia': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'N° transferencia, voucher...',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alumno'].queryset = Student.objects.filter(
            estado__in=['ACTIVO', 'CONGELADO']
        ).order_by('apellido', 'nombre')
        self.fields['plan'].queryset = PlanPago.objects.filter(activo=True)
        self.fields['plan'].required = False

        # Si es creación, prellenar mes/año actuales
        if not self.instance.pk:
            hoy = timezone.now().date()
            self.initial.setdefault('mes', hoy.month)
            self.initial.setdefault('anio', hoy.year)

    def clean(self):
        cleaned = super().clean()
        estado = cleaned.get('estado')
        metodo = cleaned.get('metodo_pago')
        fecha_pago = cleaned.get('fecha_pago')
        mes = cleaned.get('mes')
        anio = cleaned.get('anio')
        alumno = cleaned.get('alumno')

        # Si está PAGADO, exigir método y fecha
        if estado == Pago.Estado.PAGADO:
            if not metodo:
                self.add_error('metodo_pago',
                               'Obligatorio cuando el estado es PAGADO.')
            if not fecha_pago:
                cleaned['fecha_pago'] = timezone.now().date()

        # Validar mes/año razonable
        if anio and (anio < 2020 or anio > 2100):
            self.add_error('anio', 'Año fuera de rango.')
        if mes and (mes < 1 or mes > 12):
            self.add_error('mes', 'Mes inválido.')

        # Unicidad manual (para dar mejor error)
        if alumno and mes and anio:
            qs = Pago.objects.filter(alumno=alumno, mes=mes, anio=anio)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f'Ya existe un pago registrado para {alumno} en '
                    f'{dict(MESES)[mes]} {anio}.'
                )
        return cleaned


class PagoRapidoForm(forms.Form):
    """Formulario para registrar pago rápido desde el dashboard."""

    alumno = forms.ModelChoiceField(
        queryset=Student.objects.filter(estado='ACTIVO').order_by('apellido'),
        widget=forms.Select(attrs={'class': BASE_INPUT}),
    )
    plan = forms.ModelChoiceField(
        queryset=PlanPago.objects.filter(activo=True),
        widget=forms.Select(attrs={'class': BASE_INPUT}),
        required=False,
    )
    mes = forms.ChoiceField(
        choices=MESES, widget=forms.Select(attrs={'class': BASE_INPUT})
    )
    anio = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': BASE_INPUT})
    )
    monto = forms.DecimalField(
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': BASE_INPUT, 'step': '100'}),
    )
    metodo_pago = forms.ChoiceField(
        choices=Pago.Metodo.choices,
        widget=forms.Select(attrs={'class': BASE_INPUT}),
    )
    referencia = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': BASE_INPUT}),
    )


class GenerarMensualidadesForm(forms.Form):
    """Formulario para generar mensualidades en masa."""

    mes = forms.ChoiceField(
        choices=MESES,
        widget=forms.Select(attrs={'class': BASE_INPUT}),
        label='Mes',
    )
    anio = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': BASE_INPUT}),
        label='Año',
    )
    incluir_inactivos = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        label='Incluir alumnos inactivos',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoy = timezone.now().date()
        self.initial.setdefault('mes', hoy.month)
        self.initial.setdefault('anio', hoy.year)


class PromocionForm(forms.ModelForm):
    class Meta:
        model = Promocion
        fields = ['nombre', 'descripcion', 'tipo', 'valor',
                  'fecha_inicio', 'fecha_fin', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': BASE_INPUT}),
            'descripcion': forms.Textarea(attrs={'class': BASE_TEXTAREA, 'rows': 2}),
            'tipo': forms.Select(attrs={'class': BASE_INPUT}),
            'valor': forms.NumberInput(attrs={'class': BASE_INPUT, 'step': '100'}),
            'fecha_inicio': forms.DateInput(attrs={'class': BASE_INPUT, 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': BASE_INPUT, 'type': 'date'}),
            'activa': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        }