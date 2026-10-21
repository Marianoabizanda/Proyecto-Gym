from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Activity(models.Model):
    """Representa una disciplina o tipo de actividad deportiva del gimnasio (ej. Funcional, Spinning, Yoga)."""

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre de la actividad',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descripción',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activa',
        help_text='Indica si la actividad está disponible para programar clases.',
    )

    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['name']

    def __str__(self):
        return self.name


class ClassSchedule(models.Model):
    """Representa un horario semanal recurrente de una actividad a cargo de un profesor y con cupo limitado."""

    class DayOfWeek(models.IntegerChoices):
        LUNES = 1, 'Lunes'
        MARTES = 2, 'Martes'
        MIERCOLES = 3, 'Miércoles'
        JUEVES = 4, 'Jueves'
        VIERNES = 5, 'Viernes'
        SABADO = 6, 'Sábado'
        DOMINGO = 7, 'Domingo'

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='Actividad',
    )
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assigned_schedules',
        limit_choices_to={'role': 'PROFESOR'},
        verbose_name='Profesor',
    )
    day_of_week = models.PositiveSmallIntegerField(
        choices=DayOfWeek.choices,
        verbose_name='Día de la semana',
    )
    start_time = models.TimeField(
        verbose_name='Hora de inicio',
    )
    end_time = models.TimeField(
        verbose_name='Hora de fin',
    )
    capacity = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(1, message='El cupo debe ser de al menos 1 socio.')],
        verbose_name='Cupo máximo',
        help_text='Cantidad máxima de socios admitidos en este horario.',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Horario activo',
        help_text='Indica si el horario está activo para recibir inscripciones.',
    )

    class Meta:
        verbose_name = 'Horario de Clase'
        verbose_name_plural = 'Horarios de Clases'
        ordering = ['day_of_week', 'start_time']

    def clean(self):
        super().clean()
        # 1. Validación de coherencia temporal (end_time posterior a start_time)
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({
                'end_time': 'La hora de fin debe ser posterior a la hora de inicio.'
            })

        # 2. Validación de cupo mayor a 0
        if self.capacity is not None and self.capacity <= 0:
            raise ValidationError({
                'capacity': 'El cupo máximo debe ser de al menos 1 socio.'
            })

        # 3. Validación de rol PROFESOR
        if self.professor_id and hasattr(self.professor, 'is_professor_role'):
            if not self.professor.is_professor_role():
                raise ValidationError({
                    'professor': 'El usuario asignado debe tener el rol de Profesor.'
                })

    @property
    def enrolled_count(self):
        """Cantidad de socios actualmente inscriptos en este horario."""
        return self.enrollments.count()

    @property
    def available_capacity(self):
        """Cupos libres restantes."""
        return max(self.capacity - self.enrolled_count, 0)

    @property
    def is_full(self):
        """Indica si el cupo del horario está completo."""
        return self.enrolled_count >= self.capacity

    def __str__(self):
        start = self.start_time.strftime('%H:%M') if self.start_time else ''
        end = self.end_time.strftime('%H:%M') if self.end_time else ''
        return f"{self.activity.name} - {self.get_day_of_week_display()} {start} a {end}"


class ClassEnrollment(models.Model):
    """Representa la inscripción de un socio a un horario de clase específico."""

    schedule = models.ForeignKey(
        ClassSchedule,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Horario de clase',
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_enrollments',
        limit_choices_to={'role': 'SOCIO'},
        verbose_name='Socio',
    )
    enrolled_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y hora de inscripción',
    )

    class Meta:
        verbose_name = 'Inscripción a Clase'
        verbose_name_plural = 'Inscripciones a Clases'
        ordering = ['-enrolled_at']
        constraints = [
            models.UniqueConstraint(
                fields=['schedule', 'member'],
                name='unique_member_class_enrollment',
            )
        ]

    def clean(self):
        super().clean()
        # 4. Validación de rol SOCIO
        if self.member_id and hasattr(self.member, 'is_member_role'):
            if not self.member.is_member_role():
                raise ValidationError({
                    'member': 'El usuario inscripto debe tener el rol de Socio.'
                })

    def __str__(self):
        member_name = self.member.get_full_name() or self.member.username
        return f"{member_name} en {self.schedule}"
