from django import forms
from django.core.exceptions import ValidationError

from accounts.models import CustomUser
from .models import Payment, Plan, Subscription


class PlanForm(forms.ModelForm):
    """Formulario para la creación y edición de planes de entrenamiento."""

    class Meta:
        model = Plan
        fields = ['name', 'description', 'price', 'duration_days', 'is_active', 'includes_classes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Pase Libre Musculación',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detalle de los servicios o actividades que incluye...',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
            }),
            'duration_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': '30',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'includes_classes': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError('El precio del plan debe ser un monto mayor a 0.')
        return price

    def clean_duration_days(self):
        duration_days = self.cleaned_data.get('duration_days')
        if duration_days is not None and duration_days < 1:
            raise ValidationError('La duración del plan debe ser de al menos 1 día.')
        return duration_days


class SubscriptionForm(forms.ModelForm):
    """Formulario para emitir y gestionar suscripciones de socios."""

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        }),
        label='Fecha de vencimiento',
        help_text='Opcional. Si se deja en blanco, se calculará automáticamente en base a la duración del plan.',
    )

    class Meta:
        model = Subscription
        fields = ['member', 'plan', 'start_date', 'end_date', 'status']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-select'}),
            'plan': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtro de socios: solo rol SOCIO y activos.
        # Si se está editando una suscripción existente, se incluye a su socio puntual aunque esté inactivo.
        member_qs = CustomUser.objects.filter(role=CustomUser.Role.SOCIO, is_active=True)
        if self.instance and self.instance.pk and self.instance.member_id:
            member_qs = member_qs | CustomUser.objects.filter(pk=self.instance.member_id)
        self.fields['member'].queryset = member_qs.order_by('last_name', 'first_name', 'username')

        # Filtro de planes: solo planes activos.
        # Si se está editando, se incluye el plan asociado aunque haya sido desactivado posteriormente.
        plan_qs = Plan.objects.filter(is_active=True)
        if self.instance and self.instance.pk and self.instance.plan_id:
            plan_qs = plan_qs | Plan.objects.filter(pk=self.instance.plan_id)
        self.fields['plan'].queryset = plan_qs.order_by('price', 'name')

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # Si se ingresó manualmente una fecha de fin, validar que no sea previa a la fecha de inicio
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'La fecha de vencimiento no puede ser anterior a la fecha de inicio.')

        return cleaned_data


class PaymentRegistrationForm(forms.ModelForm):
    """Formulario para asentar el cobro de cuotas sobre una suscripción."""

    class Meta:
        model = Payment
        fields = ['subscription', 'amount', 'payment_date', 'payment_method', 'receipt_number', 'notes']
        widgets = {
            'subscription': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
                'readonly': 'readonly',
            }),
            'payment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'receipt_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nº de comprobante o referencia (opcional)',
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Observaciones adicionales...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Excluir suscripciones canceladas
        sub_qs = Subscription.objects.exclude(
            status=Subscription.Status.CANCELADA
        ).select_related('member', 'plan')

        # Si se edita un pago previo, permitir su suscripción original aunque haya sido cancelada luego
        if self.instance and self.instance.pk and self.instance.subscription_id:
            sub_qs = sub_qs | Subscription.objects.filter(pk=self.instance.subscription_id).select_related('member', 'plan')

        self.fields['subscription'].queryset = sub_qs.order_by('-end_date')

        # Formatear el texto de cada opción en el selector para identificar claramente al socio, su DNI, plan y estado
        self.fields['subscription'].label_from_instance = lambda obj: (
            f"{obj.member.get_full_name() or obj.member.username} (DNI: {obj.member.dni or 'S/D'}) — "
            f"{obj.plan.name} (${obj.plan.price}) [{'PENDIENTE DE PAGO' if obj.status == Subscription.Status.PENDIENTE else f'Vence: {obj.end_date}'}]"
        )

        # Sugerir monto del plan cuando el formulario recibe una suscripción inicial (vía initial)
        if not self.is_bound:
            sub_initial = self.initial.get('subscription')
            if sub_initial and not self.initial.get('amount'):
                if isinstance(sub_initial, Subscription):
                    self.initial['amount'] = sub_initial.plan.price
                elif isinstance(sub_initial, (int, str)):
                    try:
                        sub_obj = Subscription.objects.select_related('plan').get(pk=sub_initial)
                        self.initial['amount'] = sub_obj.plan.price
                    except Subscription.DoesNotExist:
                        pass

    def clean_subscription(self):
        subscription = self.cleaned_data.get('subscription')
        if subscription and subscription.status == Subscription.Status.CANCELADA:
            raise ValidationError('No se pueden registrar pagos sobre una suscripción cancelada.')
        return subscription

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError('El monto a abonar debe ser un valor mayor a 0.')
        return amount

    def clean(self):
        cleaned_data = super().clean()
        subscription = cleaned_data.get('subscription')
        amount = cleaned_data.get('amount')

        # Validación backend estricta: el importe debe coincidir exactamente con el precio oficial del plan
        if subscription and amount is not None and amount != subscription.plan.price:
            self.add_error(
                'amount',
                f"El monto a abonar (${amount}) no coincide con el valor oficial del plan '{subscription.plan.name}' (${subscription.plan.price})."
            )

        return cleaned_data

