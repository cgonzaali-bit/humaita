from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, UserChangeForm
)
from django.core.exceptions import ValidationError
from datetime import date

from .models import User


BASE_INPUT = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition'
BASE_TEXTAREA = BASE_INPUT + ' resize-y'
BASE_SELECT = BASE_INPUT
BASE_CHECKBOX = 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'


# ============================================================
# LOGIN
# ============================================================
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario o Email',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-blue-500',
            'placeholder': 'tu@email.com',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-blue-500',
            'placeholder': '••••••••',
        }),
    )

    def clean_username(self):
        """Permite login con username o email."""
        username = self.cleaned_data.get('username')
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                return user.username
            except User.DoesNotExist:
                pass
        return username


# ============================================================
# STAFF: CREAR
# ============================================================
class StaffCreateForm(UserCreationForm):
    """
    Formulario completo para crear un miembro del staff
    (instructor, monitor, profesor o admin).
    """

    class Meta:
        model = User
        fields = [
            # Credenciales
            'username', 'email', 'password1', 'password2',
            # Datos personales
            'first_name', 'last_name', 'telefono', 'foto_perfil',
            # Rol y cinturón
            'role', 'cinturon_actual', 'grados_cinturon',
            # Perfil de instructor
            'fecha_inicio_ensenanza', 'biografia', 'especialidades',
            'certificaciones', 'profesor_mentor', 'horario_disponible',
            # Estado
            'activo',
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'usuario123',
                'autocomplete': 'off',
            }),
            'email': forms.EmailInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'instructor@dojo.com',
            }),
            'first_name': forms.TextInput(attrs={
                'class': BASE_INPUT, 'placeholder': 'Juan',
            }),
            'last_name': forms.TextInput(attrs={
                'class': BASE_INPUT, 'placeholder': 'Pérez',
            }),
            'telefono': forms.TextInput(attrs={
                'class': BASE_INPUT, 'placeholder': '+56 9 1234 5678',
            }),
            'foto_perfil': forms.FileInput(attrs={
                'class': BASE_INPUT, 'accept': 'image/*',
            }),
            'role': forms.Select(attrs={'class': BASE_SELECT, 'id': 'id_role'}),
            'cinturon_actual': forms.Select(attrs={
                'class': BASE_SELECT, 'id': 'id_cinturon_actual',
            }),
            'grados_cinturon': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'min': 0, 'max': 4,
            }),
            'fecha_inicio_ensenanza': forms.DateInput(attrs={
                'class': BASE_INPUT, 'type': 'date',
            }),
            'biografia': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 3,
                'placeholder': 'Trayectoria deportiva...',
            }),
            'especialidades': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: Guardia, finalizaciones, wrestling',
            }),
            'certificaciones': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
                'placeholder': 'Certificaciones, cursos, etc.',
            }),
            'profesor_mentor': forms.Select(attrs={'class': BASE_SELECT}),
            'horario_disponible': forms.TextInput(attrs={
                'class': BASE_INPUT,
                'placeholder': 'Ej: L-M-V tardes, Sábados mañana',
            }),
            'activo': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        }
        labels = {
            'role': 'Rol en el sistema',
            'cinturon_actual': 'Cinturón',
            'grados_cinturon': 'Grados (0-4)',
            'fecha_inicio_ensenanza': 'Inicio como instructor',
            'profesor_mentor': 'Profesor mentor',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo instructores/admins existentes pueden ser mentores
        self.fields['profesor_mentor'].queryset = User.objects.filter(
            role__in=['SUPER_ADMIN', 'ADMIN', 'INSTRUCTOR'],
            activo=True,
        ).order_by('last_name', 'first_name')
        self.fields['profesor_mentor'].required = False
        self.fields['foto_perfil'].required = False
        self.fields['email'].required = True

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        cinturon = cleaned.get('cinturon_actual')

        # Si va a ser instructor, debe ser azul o superior
        if role == User.Role.INSTRUCTOR and cinturon == User.Cinturon.BLANCO:
            self.add_error(
                'cinturon_actual',
                'Para ser instructor se requiere cinturón azul o superior.'
            )

        return cleaned

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe un usuario con este email.')
        return email


# ============================================================
# STAFF: EDITAR
# ============================================================
class StaffUpdateForm(forms.ModelForm):
    """Formulario para editar un miembro del staff existente."""

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'telefono', 'foto_perfil',
            'role', 'cinturon_actual', 'grados_cinturon',
            'fecha_inicio_ensenanza', 'biografia', 'especialidades',
            'certificaciones', 'profesor_mentor', 'horario_disponible',
            'activo',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': BASE_INPUT}),
            'email': forms.EmailInput(attrs={'class': BASE_INPUT}),
            'first_name': forms.TextInput(attrs={'class': BASE_INPUT}),
            'last_name': forms.TextInput(attrs={'class': BASE_INPUT}),
            'telefono': forms.TextInput(attrs={'class': BASE_INPUT}),
            'foto_perfil': forms.FileInput(attrs={
                'class': BASE_INPUT, 'accept': 'image/*',
            }),
            'role': forms.Select(attrs={'class': BASE_SELECT}),
            'cinturon_actual': forms.Select(attrs={'class': BASE_SELECT}),
            'grados_cinturon': forms.NumberInput(attrs={
                'class': BASE_INPUT, 'min': 0, 'max': 4,
            }),
            'fecha_inicio_ensenanza': forms.DateInput(attrs={
                'class': BASE_INPUT, 'type': 'date',
            }),
            'biografia': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 3,
            }),
            'especialidades': forms.TextInput(attrs={'class': BASE_INPUT}),
            'certificaciones': forms.Textarea(attrs={
                'class': BASE_TEXTAREA, 'rows': 2,
            }),
            'profesor_mentor': forms.Select(attrs={'class': BASE_SELECT}),
            'horario_disponible': forms.TextInput(attrs={'class': BASE_INPUT}),
            'activo': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Excluirse a sí mismo de posibles mentores
        qs = User.objects.filter(
            role__in=['SUPER_ADMIN', 'ADMIN', 'INSTRUCTOR'],
            activo=True,
        ).order_by('last_name', 'first_name')
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        self.fields['profesor_mentor'].queryset = qs

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        cinturon = cleaned.get('cinturon_actual')

        if role == User.Role.INSTRUCTOR and cinturon == User.Cinturon.BLANCO:
            self.add_error(
                'cinturon_actual',
                'Para ser instructor se requiere cinturón azul o superior.'
            )
        return cleaned

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe otro usuario con este email.')
        return email