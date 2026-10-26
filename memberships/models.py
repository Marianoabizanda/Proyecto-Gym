import datetime
from django.conf import settings
from django.db import models
from django.utils import timezone


class Plan(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Plan',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descripción',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio ($)',
    )
    duration_days = models.PositiveIntegerField(
        default=30,
        verbose_name='Duración (en días)',
        help_text='Cantidad de días de cobertura de la suscripción (ej. 30 para mensual).',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Plan Activo',
        help_text='Indica si el plan está disponible para nuevas suscripciones.',
    )
    includes_classes = models.BooleanField(
        default=False,
        verbose_name='Incluye Clases Grupales',
        help_text='Indica si la suscripción a este plan habilita la inscripción a clases.',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización',
    )

    class Meta:
        verbose_name = 'Plan de Gimnasio'
        verbose_name_plural = 'Planes de Gimnasio'
        ordering = ['price', 'name']

    def __str__(self):
        return f"{self.name} - ${self.price}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Pago'
        ACTIVA = 'ACTIVA', 'Activa'
        CANCELADA = 'CANCELADA', 'Cancelada'

    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        limit_choices_to={'role': 'SOCIO'},
        verbose_name='Socio',
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name='Plan contratado',
    )
    start_date = models.DateField(
        default=timezone.localdate,
        verbose_name='Fecha de inicio',
    )
    end_date = models.DateField(
        blank=True,
        verbose_name='Fecha de vencimiento',
        help_text='Si se deja en blanco, se calculará automáticamente en base al plan.',
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVA,
        verbose_name='Estado administrativo',
        help_text='Estado administrativo. El vencimiento se calcula de forma dinámica según la fecha.',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de emisión',
    )

    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'
        ordering = ['-end_date']

    def save(self, *args, **kwargs):
        # Si no se especificó end_date, se calcula automáticamente: start_date + (duration_days - 1)
        # para que incluya exactamente los días de cobertura contando el día de inicio.
        if not self.end_date and self.start_date and self.plan:
            days_to_add = max(self.plan.duration_days - 1, 0)
            self.end_date = self.start_date + datetime.timedelta(days=days_to_add)
        super().save(*args, **kwargs)

    def activate_from_payment(self, payment_date):
        """Activa la suscripción estableciendo el inicio en la fecha de pago y recalculando el vencimiento."""
        self.status = self.Status.ACTIVA
        self.start_date = payment_date
        days_to_add = max(self.plan.duration_days - 1, 0)
        self.end_date = payment_date + datetime.timedelta(days=days_to_add)
        self.save(update_fields=['status', 'start_date', 'end_date'])

    @property
    def effective_status(self):
        """Devuelve el estado dinámico: PENDIENTE, CANCELADA, FUTURA, ACTIVA o VENCIDA según la fecha actual."""
        if self.status == self.Status.CANCELADA:
            return 'CANCELADA'
        if self.status == self.Status.PENDIENTE:
            return 'PENDIENTE'
        today = timezone.localdate()
        if self.start_date and self.start_date > today:
            return 'FUTURA'
        if self.end_date and self.end_date < today:
            return 'VENCIDA'
        return 'ACTIVA'

    @property
    def is_current(self):
        """Verifica si la suscripción está vigente hoy (start_date <= today <= end_date y no cancelada)."""
        return self.effective_status == 'ACTIVA'

    @property
    def days_left(self):
        """Calcula los días restantes de vigencia."""
        today = timezone.localdate()
        if not self.is_current or not self.end_date:
            return 0
        return max((self.end_date - today).days, 0)

    def __str__(self):
        return f"{self.member.get_full_name() or self.member.username} - {self.plan.name} ({self.effective_status}: {self.end_date})"


class Payment(models.Model):
    class Method(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia Bancaria'
        DEBITO = 'DEBITO', 'Tarjeta de Débito'
        CREDITO = 'CREDITO', 'Tarjeta de Crédito'
        OTRO = 'OTRO', 'Otro'

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='Suscripción asociada',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto abonado ($)',
        help_text='Monto histórico cobrado en la transacción.',
    )
    payment_date = models.DateField(
        default=timezone.localdate,
        verbose_name='Fecha de pago',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.EFECTIVO,
        verbose_name='Método de pago',
    )
    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Nº Comprobante / Referencia',
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Observaciones',
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_payments',
        verbose_name='Cobrado por',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y hora de registro',
    )

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-payment_date', '-created_at']

    @property
    def member(self):
        """Acceso al socio a través de la suscripción asociada."""
        return self.subscription.member

    def __str__(self):
        return f"Pago #{self.id} - ${self.amount} ({self.subscription.member.username}) - {self.payment_date}"
