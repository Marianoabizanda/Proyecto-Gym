from django.db import models


class DailyRoutine(models.Model):
    """Representa la rutina diaria general programada para un día de la semana."""

    class DayOfWeek(models.IntegerChoices):
        LUNES = 1, 'Lunes'
        MARTES = 2, 'Martes'
        MIERCOLES = 3, 'Miércoles'
        JUEVES = 4, 'Jueves'
        VIERNES = 5, 'Viernes'
        SABADO = 6, 'Sábado'
        DOMINGO = 7, 'Domingo'

    day_of_week = models.PositiveSmallIntegerField(
        choices=DayOfWeek.choices,
        unique=True,
        verbose_name='Día de la semana',
        help_text='Día de la semana en el que se ejecuta esta rutina.',
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre de la rutina',
        help_text='Ej: Tren Superior, Piernas y Core, Full Body.',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Objetivo o descripción',
        help_text='Breve indicación del objetivo o grupo muscular a trabajar.',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activa',
        help_text='Indica si esta rutina está disponible y visible para los socios en el día correspondiente.',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última modificación',
    )

    class Meta:
        verbose_name = 'Rutina Diaria'
        verbose_name_plural = 'Rutinas Diarias'
        ordering = ['day_of_week']

    def __str__(self):
        return f"{self.get_day_of_week_display()} — {self.name}"


class RoutineExercise(models.Model):
    """Representa un ejercicio individual perteneciente a una rutina diaria."""

    routine = models.ForeignKey(
        DailyRoutine,
        on_delete=models.CASCADE,
        related_name='exercises',
        verbose_name='Rutina',
    )
    name = models.CharField(
        max_length=120,
        verbose_name='Nombre del ejercicio',
        help_text='Ej: Press de banca, Sentadilla, Remo con barra.',
    )
    sets = models.PositiveSmallIntegerField(
        default=3,
        verbose_name='Series',
    )
    repetitions = models.CharField(
        max_length=50,
        verbose_name='Repeticiones',
        help_text="Ej: '10', '12', '10-12', 'Al fallo', '30 seg'.",
    )
    notes = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Observaciones / Indicaciones',
        help_text="Ej: 'RPE 8', 'Descanso 60s', 'Priorizar técnica'.",
    )
    order = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Orden de ejecución',
        help_text='Posición del ejercicio dentro de la rutina.',
    )

    class Meta:
        verbose_name = 'Ejercicio de Rutina'
        verbose_name_plural = 'Ejercicios de Rutina'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.name} ({self.sets} x {self.repetitions})"

