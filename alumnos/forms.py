from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date

from .models import Student, BeltHistory


class StudentForm(forms.ModelForm):
    """
    Formulario principal de creación/edición de alumnos.
    Incluye validaciones de edad, tutor obligatorio para menores,
    y validación de foto.
    """

    class Meta:
        model = Student
        fields = [
            # Datos personales
            'nombre', 'apellido', 'fecha_nacimiento', 'rut',
            'telefono', 'email', 'direccion', 'foto_perfil',
            # Academia
            'cinturon_actual', 'grados_cinturon', 'categoria', 'estado',
            # Tutor
            'tutor_nombre', 'tutor_telefono', 'tutor_parentesco',
            # Notas
            'notas',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Cristian',
                'autocomplete': 'off',
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: González',
                'autocomplete': 'off',
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'rut': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: 12345678-9',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+56 9 1234 5678',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'alumno@email.com',
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Dirección completa',
            }),
            'foto_perfil': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*',
                'id': 'id_foto_perfil',
            }),
            'cinturon_actual': forms.Select(attrs={'class': 'form-input'}),
            'grados_cinturon': forms.NumberInput(attrs={
                'class': 'form-input', 'min': 0, 'max': 4,
            }),
            'categoria': forms.Select(attrs={'class': 'form-input', 'id': 'id_categoria'}),
            'estado': forms.Select(attrs={'class': 'form-input'}),
            'tutor_nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre completo del tutor',
                'id': 'id_tutor_nombre',
            }),
            'tutor_telefono': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+56 9 1234 5678',
                'id': 'id_tutor_telefono',
            }),
            'tutor_parentesco': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Madre, Padre, Abuelo, Hermano',
                'id': 'id_tutor_parentesco',
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Observaciones del profesor...',
            }),
        }
        labels = {
            'rut': 'RUT / Documento',
            'foto_perfil': 'Foto de perfil',
            'cinturon_actual': 'Cinturón actual',
            'grados_cinturon': 'Grados (0-4)',
            'tutor_nombre': 'Nombre del tutor',
            'tutor_telefono': 'Teléfono del tutor',
            'tutor_parentesco': 'Parentesco',
        }

    # ===== VALIDACIONES =====

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if not fecha:
            return fecha

        hoy = date.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))

        if fecha > hoy:
            raise ValidationError('La fecha de nacimiento no puede ser futura.')
        if edad < 5:
            raise ValidationError('La edad mínima para ingresar es 5 años.')
        if edad > 100:
            raise ValidationError('Verifica la fecha de nacimiento.')
        return fecha

    def clean_rut(self):
        rut = self.cleaned_data.get('rut', '').strip().upper()
        if not rut:
            raise ValidationError('El RUT es obligatorio.')

        # Verificar unicidad excluyendo la instancia actual (en edición)
        qs = Student.objects.filter(rut__iexact=rut)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe un alumno con este RUT.')
        return rut

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')
        if foto and hasattr(foto, 'size'):
            if foto.size > 5 * 1024 * 1024:
                raise ValidationError('La imagen no puede superar los 5 MB.')
            if not foto.content_type.startswith('image/'):
                raise ValidationError('El archivo debe ser una imagen.')
        return foto

    def clean_grados_cinturon(self):
        grados = self.cleaned_data.get('grados_cinturon', 0)
        if grados < 0 or grados > 4:
            raise ValidationError('Los grados deben estar entre 0 y 4.')
        return grados

    def clean(self):
        """
        Validación cruzada: si el alumno es menor de 18 años,
        el tutor es obligatorio. Además, la categoría se autocalcula
        según la edad si el usuario no la especificó.
        """
        cleaned = super().clean()
        fecha = cleaned.get('fecha_nacimiento')
        categoria = cleaned.get('categoria')

        if fecha:
            hoy = date.today()
            edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))

            # Autocalcular categoría si no fue proporcionada
            if not categoria:
                if edad <= 12:
                    cleaned['categoria'] = 'INFANTIL'
                elif edad <= 17:
                    cleaned['categoria'] = 'JUVENIL'
                elif edad <= 35:
                    cleaned['categoria'] = 'ADULTO'
                else:
                    cleaned['categoria'] = 'MASTER'

            # Validar tutor para menores
            if edad < 18:
                tutor_nombre = cleaned.get('tutor_nombre', '').strip()
                tutor_telefono = cleaned.get('tutor_telefono', '').strip()

                if not tutor_nombre:
                    self.add_error(
                        'tutor_nombre',
                        'Obligatorio para alumnos menores de 18 años.'
                    )
                if not tutor_telefono:
                    self.add_error(
                        'tutor_telefono',
                        'Obligatorio para alumnos menores de 18 años.'
                    )
        return cleaned


class StudentFilterForm(forms.Form):
    """Formulario de filtros avanzados para el listado."""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Buscar por nombre, apellido o RUT...',
            'autocomplete': 'off',
            'hx-get': '/alumnos/buscar/',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#lista-alumnos',
            'hx-include': '[name="cinturon"],[name="categoria"],[name="estado"]',
            'hx-indicator': '#buscando',
        }),
    )
    cinturon = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los cinturones')] + Student.Cinturon.choices,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'hx-get': '/alumnos/buscar/',
            'hx-trigger': 'change',
            'hx-target': '#lista-alumnos',
            'hx-include': '[name="q"],[name="categoria"],[name="estado"]',
        }),
    )
    categoria = forms.ChoiceField(
        required=False,
        choices=[('', 'Todas las categorías')] + Student.Categoria.choices,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'hx-get': '/alumnos/buscar/',
            'hx-trigger': 'change',
            'hx-target': '#lista-alumnos',
            'hx-include': '[name="q"],[name="cinturon"],[name="estado"]',
        }),
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los estados')] + Student.Estado.choices,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'hx-get': '/alumnos/buscar/',
            'hx-trigger': 'change',
            'hx-target': '#lista-alumnos',
            'hx-include': '[name="q"],[name="cinturon"],[name="categoria"]',
        }),
    )


class BeltPromotionForm(forms.ModelForm):
    """Formulario para otorgar una promoción de cinturón."""

    class Meta:
        model = BeltHistory
        fields = ['cinturon_nuevo', 'grados', 'fecha_promocion', 'observaciones']
        widgets = {
            'cinturon_nuevo': forms.Select(attrs={'class': 'form-input'}),
            'grados': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 4}),
            'fecha_promocion': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.alumno = kwargs.pop('alumno', None)
        super().__init__(*args, **kwargs)
        if not self.initial.get('fecha_promocion'):
            self.initial['fecha_promocion'] = timezone.now().date()