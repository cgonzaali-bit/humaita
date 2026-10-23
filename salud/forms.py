from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date

from .models import (
    Enfermedad, Alergia, Lesion, CertificadoMedico, ContactoEmergencia
)


# Estilos base reutilizables
BASE_INPUT = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition'
BASE_TEXTAREA = BASE_INPUT + ' resize-y'
BASE_SELECT = BASE_INPUT
BASE_CHECKBOX = 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'


class EnfermedadForm(forms.ModelForm):
    class Meta:
        model = Enfermedad
        fields = ['nombre', 'descripcion', 'gravedad', 'tratamiento',
                  'medicamentos', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: Asma, Cardiopatía, Epilepsia',
                'autofocus': True,
            }),
            'descripcion': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 3,
                'placeholder': 'Describe brevemente la condición...',
            }),
            'gravedad': forms.Select(attrs={'class': BASE_SELECT}),
            'tratamiento': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
                'placeholder': 'Tratamiento actual (opcional)',
            }),
            'medicamentos': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
                'placeholder': 'Ej: Salbutamol inhalador',
            }),
            'activa': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        }


class AlergiaForm(forms.ModelForm):
    class Meta:
        model = Alergia
        fields = ['tipo', 'descripcion', 'severidad', 'tratamiento',
                  'requiere_epipen', 'activa']
        widgets = {
            'tipo': forms.Select(attrs={'class': BASE_SELECT}),
            'descripcion': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: Penicilina, maní, polen',
                'autofocus': True,
            }),
            'severidad': forms.Select(attrs={'class': BASE_SELECT}),
            'tratamiento': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
                'placeholder': 'Tratamiento en caso de reacción',
            }),
            'requiere_epipen': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
            'activa': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        }


class LesionForm(forms.ModelForm):
    class Meta:
        model = Lesion
        fields = ['zona_cuerpo', 'descripcion', 'fecha_lesion', 'estado',
                  'tratamiento', 'observaciones']
        widgets = {
            'zona_cuerpo': forms.Select(attrs={'class': BASE_SELECT}),
            'descripcion': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 3,
                'placeholder': 'Describe la lesión y cómo ocurrió',
            }),
            'fecha_lesion': forms.DateInput(attrs={
                'class': BASE_INPUT, 'type': 'date',
            }),
            'estado': forms.Select(attrs={'class': BASE_SELECT}),
            'tratamiento': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
            'observaciones': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
        }

    def clean_fecha_lesion(self):
        fecha = self.cleaned_data.get('fecha_lesion')
        if fecha and fecha > timezone.now().date():
            raise ValidationError('La fecha de la lesión no puede ser futura.')
        return fecha


class CertificadoMedicoForm(forms.ModelForm):
    class Meta:
        model = CertificadoMedico
        fields = ['archivo', 'fecha_emision', 'fecha_vencimiento',
                  'medico', 'numero_registro', 'apto_para_competir',
                  'observaciones']
        widgets = {
            'archivo': forms.FileInput(attrs={
                'class': BASE_INPUT,
                'accept': 'image/*,application/pdf',
            }),
            'fecha_emision': forms.DateInput(attrs={
                'class': BASE_INPUT, 'type': 'date',
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': BASE_INPUT, 'type': 'date',
            }),
            'medico': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Nombre del médico',
            }),
            'numero_registro': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'N° de registro profesional',
            }),
            'apto_para_competir': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
            'observaciones': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
        }

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if archivo and hasattr(archivo, 'size'):
            if archivo.size > 10 * 1024 * 1024:
                raise ValidationError('El archivo no puede superar 10 MB.')
        return archivo

    def clean(self):
        cleaned = super().clean()
        emision = cleaned.get('fecha_emision')
        vencimiento = cleaned.get('fecha_vencimiento')

        if emision and vencimiento:
            if vencimiento <= emision:
                self.add_error(
                    'fecha_vencimiento',
                    'La fecha de vencimiento debe ser posterior a la emisión.'
                )
            # Un certificado deportivo suele durar máximo 1 año
            delta = (vencimiento - emision).days
            if delta > 366:
                self.add_error(
                    'fecha_vencimiento',
                    'La vigencia no puede superar 1 año desde la emisión.'
                )
        return cleaned


class ContactoEmergenciaForm(forms.ModelForm):
    class Meta:
        model = ContactoEmergencia
        fields = ['nombre', 'telefono', 'telefono_alternativo', 'parentesco',
                  'es_tutor_legal', 'notas']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Nombre completo',
            }),
            'telefono': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': '+56 9 XXXX XXXX',
            }),
            'telefono_alternativo': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Opcional',
            }),
            'parentesco': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: Madre, Padre, Cónyuge, Hermano',
            }),
            'es_tutor_legal': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
            'notas': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
        }