from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from alumnos.models import Student
from .models import Evento, InscripcionEvento, FotoEvento


BASE_INPUT = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition'
BASE_TEXTAREA = BASE_INPUT + ' resize-y'
BASE_CHECKBOX = 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['nombre', 'tipo', 'descripcion', 'fecha', 'fecha_fin',
                  'lugar', 'costo', 'cupo_maximo', 'estado',
                  'cinturon_objetivo', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: Seminario de guardia abierta',
                'autofocus': True,
            }),
            'tipo': forms.Select(attrs={'class': BASE_INPUT}),
            'descripcion': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 3,
                'placeholder': 'Detalles del evento...',
            }),
            'fecha': forms.DateTimeInput(attrs={
                'class': BASE_INPUT, 'type': 'datetime-local',
            }),
            'fecha_fin': forms.DateTimeInput(attrs={
                'class': BASE_INPUT, 'type': 'datetime-local',
            }),
            'lugar': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: Dojo principal',
            }),
            'costo': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'step': '500', 'min': '0',
            }),
            'cupo_maximo': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'min': '1',
            }),
            'estado': forms.Select(attrs={'class': BASE_INPUT}),
            'cinturon_objetivo': forms.Select(attrs={'class': BASE_INPUT}),
            'activo': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        }

    def clean(self):
        cleaned = super().clean()
        fecha = cleaned.get('fecha')
        fecha_fin = cleaned.get('fecha_fin')

        if fecha and fecha_fin and fecha_fin < fecha:
            self.add_error('fecha_fin', 'La fecha de fin no puede ser anterior al inicio.')

        return cleaned


class InscripcionForm(forms.ModelForm):
    """Formulario para inscribir un alumno a un evento."""

    class Meta:
        model = InscripcionEvento
        fields = ['alumno', 'estado_pago', 'monto_pagado',
                  'fecha_pago', 'metodo_pago', 'observaciones']
        widgets = {
            'alumno': forms.Select(attrs={'class': BASE_INPUT}),
            'estado_pago': forms.Select(attrs={'class': BASE_INPUT}),
            'monto_pagado': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'step': '500', 'min': '0',
            }),
            'fecha_pago': forms.DateInput(attrs={
                'class': BASE_INPUT, 'type': 'date',
            }),
            'metodo_pago': forms.TextInput(attrs={'class': BASE_INPUT}),
            'observaciones': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
        }

    def __init__(self, *args, **kwargs):
        self.evento = kwargs.pop('evento', None)
        super().__init__(*args, **kwargs)

        if self.evento:
            # Excluir alumnos ya inscritos
            ya_inscritos = InscripcionEvento.objects.filter(
                evento=self.evento
            ).values_list('alumno_id', flat=True)

            self.fields['alumno'].queryset = Student.objects.filter(
                estado='ACTIVO'
            ).exclude(pk__in=ya_inscritos).order_by('apellido', 'nombre')

            # Prellenar con el costo del evento
            if not self.instance.pk:
                self.initial['monto_pagado'] = self.evento.costo

    def clean(self):
        cleaned = super().clean()
        estado = cleaned.get('estado_pago')
        if estado == InscripcionEvento.EstadoPago.PAGADO:
            if not cleaned.get('fecha_pago'):
                cleaned['fecha_pago'] = timezone.now().date()
        return cleaned


class InscripcionMasivaForm(forms.Form):
    """Inscripción masiva: seleccionar varios alumnos a la vez."""

    alumnos = forms.ModelMultipleChoiceField(
        queryset=Student.objects.filter(estado='ACTIVO').order_by('apellido'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-1'}),
        label='Seleccionar alumnos',
    )
    eximir_pago = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        label='Eximir del pago (inscripción gratuita)',
    )

    def __init__(self, *args, **kwargs):
        self.evento = kwargs.pop('evento', None)
        super().__init__(*args, **kwargs)
        if self.evento:
            ya_inscritos = InscripcionEvento.objects.filter(
                evento=self.evento
            ).values_list('alumno_id', flat=True)
            self.fields['alumnos'].queryset = Student.objects.filter(
                estado='ACTIVO'
            ).exclude(pk__in=ya_inscritos).order_by('apellido', 'nombre')


class ResultadoForm(forms.ModelForm):
    """Para registrar el resultado de un alumno en el evento."""

    class Meta:
        model = InscripcionEvento
        fields = ['resultado', 'posicion', 'categoria_competencia', 'observaciones']
        widgets = {
            'resultado': forms.Select(attrs={'class': BASE_INPUT}),
            'posicion': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'min': '1',
            }),
            'categoria_competencia': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: Adulto - Pluma - Azul',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
        }


class FotoEventoForm(forms.ModelForm):
    class Meta:
        model = FotoEvento
        fields = ['imagen', 'titulo', 'descripcion']
        widgets = {
            'imagen': forms.FileInput(attrs={
                'class': BASE_INPUT, 'accept': 'image/*',
            }),
            'titulo': forms.TextInput(attrs={'class': BASE_INPUT}),
            'descripcion': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
        }

    def clean_imagen(self):
        img = self.cleaned_data.get('imagen')
        if img and hasattr(img, 'size'):
            if img.size > 8 * 1024 * 1024:
                raise ValidationError('La imagen no puede superar 8 MB.')
        return img