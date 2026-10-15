from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        PROFESOR = 'PROFESOR', 'Profesor'
        SOCIO = 'SOCIO', 'Socio'

    role = models.CharField(
        max_length=15,
        choices=Role.choices,
        default=Role.SOCIO,
        verbose_name='Rol',
    )
    dni = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name='DNI',
    )
    phone = models.CharField(
        max_length=25,
        blank=True,
        verbose_name='Teléfono',
    )

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def is_admin_role(self):
        """Verifica si el usuario tiene rol ADMIN o es superusuario nativo de Django."""
        return self.role == self.Role.ADMIN or self.is_superuser

    def is_professor_role(self):
        """Verifica si el usuario tiene rol PROFESOR."""
        return self.role == self.Role.PROFESOR

    def is_member_role(self):
        """Verifica si el usuario tiene rol SOCIO."""
        return self.role == self.Role.SOCIO

    def __str__(self):
        full_name = self.get_full_name()
        display_name = full_name if full_name else self.username
        return f"{display_name} ({self.get_role_display()})"


class MemberProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='member_profile',
        limit_choices_to={'role': CustomUser.Role.SOCIO},
        verbose_name='Socio',
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de nacimiento',
    )
    medical_certificate = models.BooleanField(
        default=False,
        verbose_name='Apto físico presentado',
    )
    medical_certificate_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha del apto físico',
    )
    emergency_contact_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Contacto de emergencia (nombre)',
    )
    emergency_contact_phone = models.CharField(
        max_length=25,
        blank=True,
        verbose_name='Contacto de emergencia (teléfono)',
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Observaciones médicas / Notas',
    )

    class Meta:
        verbose_name = 'Ficha de Socio'
        verbose_name_plural = 'Fichas de Socios'

    def __str__(self):
        return f"Ficha médica de {self.user.get_full_name() or self.user.username}"

