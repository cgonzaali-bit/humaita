from django import forms
from django.utils import timezone

from alumnos.models import Student
from .models import Clase, Asistencia


BASE_INPUT = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition'
BASE_CHECKBOX = 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'


class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ['nombre', 'dia_semana', 'hora_inicio', 'hora_fin',
                  'categoria', 'instructor', 'cupo_maximo', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: Adultos - Nocturna',
                'autofocus': True,
            }),
            'dia_semana': forms.Select(attrs={'class': BASE_INPUT}),
            'hora_inicio': forms.TimeInput(attrs={
                'class': BASE_INPUT, 'type': 'time',
            }),
            'hora_fin': forms.TimeInput(attrs={
                'class': BASE_INPUT, 'type': 'time',
            }),
            'categoria': forms.Select(attrs={'class': BASE_INPUT}),
            'instructor': forms.Select(attrs={'class': BASE_INPUT}),
            'cupo_maximo': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'min': '1',
            }),
            'activo': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        }

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('hora_inicio')
        fin = cleaned.get('hora_fin')
        if inicio and fin and fin <= inicio:
            self.add_error('hora_fin', 'La hora de fin debe ser posterior al inicio.')
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from usuarios.models import User
        # Solo usuarios con nivel de instructor (azul+)
        self.fields['instructor'].queryset = User.objects.filter(
            role__in=['SUPER_ADMIN', 'ADMIN', 'INSTRUCTOR'],
            cinturon_actual__in=['AZUL', 'MORADO', 'MARRON', 'NEGRO'],
            activo=True,
        ).order_by('last_name', 'first_name')
        self.fields['instructor'].required = False
        self.fields['instructor'].empty_label = '— Sin asignar —'


class CheckInForm(forms.Form):
    """
    Formulario de check-in rápido por búsqueda de nombre o RUT.
    NO guarda por sí solo; la vista procesa la búsqueda.
    """
    q = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full text-lg px-4 py-3 border-2 border-gray-300 rounded-xl '
                     'focus:ring-2 focus:ring-green-500 focus:border-green-500',
            'placeholder': '🔍 Buscar por nombre o RUT...',
            'autofocus': True,
            'autocomplete': 'off',
            'hx-get': '/asistencia/check-in/buscar/',
            'hx-trigger': 'keyup changed delay:200ms',
            'hx-target': '#resultados-busqueda',
            'hx-include': '[name="clase_id"],[name="fecha"]',
        }),
        label='Buscar alumno',
    )


class AsistenciaManualForm(forms.Form):
    """
    Formulario para marcar asistencia de un grupo completo.
    Usa checkboxes generados dinámicamente.
    """
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': BASE_INPUT, 'type': 'date',
        }),
        initial=timezone.now().date,
        label='Fecha',
    )
    clase = forms.ModelChoiceField(
        queryset=Clase.objects.filter(activo=True).order_by('dia_semana', 'hora_inicio'),
        widget=forms.Select(attrs={'class': BASE_INPUT}),
        label='Clase',
    )