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

