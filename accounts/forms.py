from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    """Formulario para crear usuarios desde el panel de administración."""

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'dni', 'phone', 'role')


class CustomUserChangeForm(UserChangeForm):
    """Formulario para editar usuarios desde el panel de administración."""

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'dni', 'phone', 'role', 'is_active', 'is_staff', 'is_superuser')


class CustomAuthenticationForm(AuthenticationForm):
    """Formulario de inicio de sesión estilizado con Bootstrap 5."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre de usuario',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Contraseña',
        })


class MemberRegistrationForm(UserCreationForm):
    """Formulario público de registro para nuevos socios."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Carlos'}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Gómez'}),
    )
    email = forms.EmailField(
        required=True,
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'nombre@ejemplo.com'}),
    )
    dni = forms.CharField(
        max_length=20,
        required=True,
        label='DNI / Documento',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sin puntos'}),
    )
    phone = forms.CharField(
        max_length=25,
        required=False,
        label='Teléfono de contacto',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. +54 9 11 1234-5678'}),
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'dni', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Elige un usuario único',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Crea una contraseña segura',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Repite la contraseña',
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        # El registro público siempre asigna el rol de SOCIO por seguridad
        user.role = CustomUser.Role.SOCIO
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Formulario para que cualquier usuario pueda actualizar su perfil básico."""

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'dni', 'phone')
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo Electrónico',
            'dni': 'DNI',
            'phone': 'Teléfono',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

