import datetime
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from accounts.models import CustomUser
from .forms import PaymentRegistrationForm, PlanForm, SubscriptionForm
from .models import Payment, Plan, Subscription


# ==============================================================================
# MIXINS DE PERMISOS Y CONTROL DE ACCESO
# ==============================================================================

class BaseRoleRequiredMixin(AccessMixin):
    """Mixin base que asegura una diferenciación explícita de accesos:

    1. Si el usuario NO está autenticado: es redirigido a LOGIN_URL.
    2. Si el usuario está autenticado pero NO cuenta con el rol requerido: recibe 403 Forbidden (PermissionDenied).
    """

    permission_denied_message = "No tienes permisos para acceder a esta sección."

    def check_role(self, user):
        """Método a sobreescribir por las subclases para validar el rol específico."""
        return False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.check_role(request.user):
            raise PermissionDenied(self.permission_denied_message)
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(BaseRoleRequiredMixin):
    """Acceso exclusivo para administradores o superusuarios del sistema."""

    permission_denied_message = "Se requieren permisos de Administrador para realizar esta acción."

    def check_role(self, user):
        return user.is_admin_role()


class StaffOrProfessorRequiredMixin(BaseRoleRequiredMixin):
    """Permite el acceso a Administradores y Profesores (para consulta de socios y planes)."""

    permission_denied_message = "Acceso restringido a Administradores y Profesores."

    def check_role(self, user):
        return user.is_admin_role() or user.is_professor_role()


class MemberRequiredMixin(BaseRoleRequiredMixin):
    """Permite el acceso exclusivo a usuarios con rol SOCIO para su información personal."""

    permission_denied_message = "Acceso restringido al portal de socios."

    def check_role(self, user):
        return user.is_member_role()


# ==============================================================================
# VISTAS DE PLANES
# ==============================================================================

class PlanListView(StaffOrProfessorRequiredMixin, ListView):
    """Lista de planes del gimnasio.

    El Administrador visualiza planes activos e inactivos para gestión.
    El Profesor visualiza únicamente los planes activos para consulta comercial.
    """

    model = Plan
    template_name = 'memberships/plan_list.html'
    context_object_name = 'plans'

    def get_queryset(self):
        if self.request.user.is_admin_role():
            return Plan.objects.all().order_by('price', 'name')
        return Plan.objects.filter(is_active=True).order_by('price', 'name')


class PlanCreateView(AdminRequiredMixin, CreateView):
    """Alta de nuevo plan de entrenamiento (exclusivo ADMIN)."""

    model = Plan
    form_class = PlanForm
    template_name = 'memberships/plan_form.html'
    success_url = reverse_lazy('memberships:plan_list')

    def form_valid(self, form):
        messages.success(self.request, f"El plan '{form.instance.name}' fue creado correctamente.")
        return super().form_valid(form)


class PlanUpdateView(AdminRequiredMixin, UpdateView):
    """Edición o desactivación de un plan existente (exclusivo ADMIN)."""

    model = Plan
    form_class = PlanForm
    template_name = 'memberships/plan_form.html'
    success_url = reverse_lazy('memberships:plan_list')

    def form_valid(self, form):
        messages.success(self.request, f"El plan '{form.instance.name}' fue actualizado con éxito.")
        return super().form_valid(form)


# ==============================================================================
# VISTAS DE SOCIOS Y SUSCRIPCIONES
# ==============================================================================

class MemberListView(StaffOrProfessorRequiredMixin, ListView):
    """Padrón de socios con buscador y estado actual de membresía."""

    model = CustomUser
    template_name = 'memberships/member_list.html'
    context_object_name = 'members'
    paginate_by = 15

    def get_queryset(self):
        qs = CustomUser.objects.filter(role=CustomUser.Role.SOCIO).select_related(
            'member_profile'
        ).prefetch_related('subscriptions__plan').order_by('last_name', 'first_name')

        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(dni__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')

        # Asigna la suscripción vigente a cada socio de la página en memoria usando el prefetch
        for member in context['members']:
            member.current_subscription = next(
                (s for s in member.subscriptions.all() if s.is_current),
                None
            )

        return context


class MemberDetailView(StaffOrProfessorRequiredMixin, DetailView):
    """Ficha integral del socio: datos personales, ficha médica, suscripción actual e histórico de pagos."""

    model = CustomUser
    template_name = 'memberships/member_detail.html'
    context_object_name = 'member'

    def get_queryset(self):
        return CustomUser.objects.filter(role=CustomUser.Role.SOCIO).select_related('member_profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.object

        subscriptions = member.subscriptions.select_related('plan').order_by('-end_date')
        context['subscriptions'] = subscriptions
        context['current_subscription'] = next((s for s in subscriptions if s.is_current), None)

        context['payments'] = Payment.objects.filter(
            subscription__member=member
        ).select_related('subscription__plan', 'registered_by').order_by('-payment_date', '-created_at')

        return context


class SubscriptionCreateView(AdminRequiredMixin, CreateView):
    """Emisión o renovación manual de una suscripción para un socio (exclusivo ADMIN).

    Valida que no exista superposición de fechas entre la nueva suscripción y otra
    suscripción administrativa ACTIVA preexistente del mismo socio.
    """

    model = Subscription
    form_class = SubscriptionForm
    template_name = 'memberships/subscription_form.html'

    def get_initial(self):
        initial = super().get_initial()
        member_id = self.request.GET.get('member')
        if member_id:
            initial['member'] = member_id
        return initial

    def form_valid(self, form):
        member = form.cleaned_data.get('member')
        plan = form.cleaned_data.get('plan')
        new_start = form.cleaned_data.get('start_date')
        new_end = form.cleaned_data.get('end_date')

        # Si end_date no se ingresó en el formulario, se calcula temporalmente
        # con la misma regla del modelo: start_date + (duration_days - 1)
        if not new_end and new_start and plan:
            days_to_add = max(plan.duration_days - 1, 0)
            new_end = new_start + datetime.timedelta(days=days_to_add)

        # Requisito 2: Validar superposición de fechas con suscripciones activas del socio.
        # Dos intervalos [A, B] y [C, D] se superponen si start_date <= new_end y end_date >= new_start.
        if new_start and new_end:
            overlapping_sub = Subscription.objects.filter(
                member=member,
                status=Subscription.Status.ACTIVA,
                start_date__lte=new_end,
                end_date__gte=new_start,
            ).select_related('plan').first()

            if overlapping_sub:
                form.add_error(
                    None,
                    f"El período solicitado ({new_start.strftime('%d/%m/%Y')} al {new_end.strftime('%d/%m/%Y')}) "
                    f"se superpone con otra suscripción activa existente "
                    f"({overlapping_sub.plan.name}: {overlapping_sub.start_date.strftime('%d/%m/%Y')} al {overlapping_sub.end_date.strftime('%d/%m/%Y')}). "
                    "No se permiten membresías con rangos de fechas superpuestos."
                )
                return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Suscripción al plan '{self.object.plan.name}' registrada para {member.get_full_name() or member.username}."
        )
        return response

    def get_success_url(self):
        return reverse_lazy('memberships:member_detail', kwargs={'pk': self.object.member.pk})


class SubscriptionCancelView(AdminRequiredMixin, View):
    """Cancela administrativamente una suscripción ante baja anticipada (Requisito 5: exclusivamente POST)."""

    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        subscription = get_object_or_404(Subscription, pk=pk)
        subscription.status = Subscription.Status.CANCELADA
        subscription.save(update_fields=['status'])

        messages.info(
            request,
            f"La suscripción de {subscription.member.get_full_name() or subscription.member.username} fue cancelada."
        )
        return redirect('memberships:member_detail', pk=subscription.member.pk)


# ==============================================================================
# VISTAS DE PAGOS
# ==============================================================================

class PaymentCreateView(AdminRequiredMixin, CreateView):
    """Registro contable de cobros sobre una suscripción (exclusivo ADMIN).

    Inyecta obligatoriamente registered_by desde request.user y bloquea suscripciones canceladas.
    Permite registrar cobros sobre suscripciones vencidas si corresponden a saldos pendientes.

    NOTA DE NEGOCIO:
    Registrar un pago sobre una suscripción vencida NO la renueva automáticamente.
    El flujo específico de renovación de membresías será definido e implementado en una etapa posterior.
    """

    model = Payment
    form_class = PaymentRegistrationForm
    template_name = 'memberships/payment_form.html'

    def get_initial(self):
        initial = super().get_initial()
        subscription_id = self.request.GET.get('subscription')
        if subscription_id:
            initial['subscription'] = subscription_id
        return initial

    def form_valid(self, form):
        # Asignación inmutable del usuario autenticado que registra el cobro
        form.instance.registered_by = self.request.user

        subscription = form.cleaned_data.get('subscription')
        if subscription and subscription.status == Subscription.Status.CANCELADA:
            form.add_error('subscription', 'No es posible registrar un pago sobre una suscripción cancelada.')
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Cobro de ${self.object.amount} registrado correctamente para "
            f"{subscription.member.get_full_name() or subscription.member.username}."
        )
        return response

    def get_success_url(self):
        subscription = self.object.subscription
        return reverse_lazy('memberships:member_detail', kwargs={'pk': subscription.member.pk})


class PaymentListView(AdminRequiredMixin, ListView):
    """Registro histórico de todos los cobros para auditoría y balance administrativo (exclusivo ADMIN)."""

    model = Payment
    template_name = 'memberships/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        return Payment.objects.select_related(
            'subscription__member', 'subscription__plan', 'registered_by'
        ).order_by('-payment_date', '-created_at')


# ==============================================================================
# PORTAL DEL SOCIO ("MI MEMBRESÍA")
# ==============================================================================

class MyMembershipView(MemberRequiredMixin, TemplateView):
    """Consulta personal del socio autenticado (utiliza exclusivamente request.user)."""

    template_name = 'memberships/my_membership.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        subscriptions = user.subscriptions.select_related('plan').order_by('-end_date')
        current_subscription = next((s for s in subscriptions if s.is_current), None)

        payments = Payment.objects.filter(
            subscription__member=user
        ).select_related('subscription__plan', 'registered_by').order_by('-payment_date', '-created_at')

        context['current_subscription'] = current_subscription
        context['has_active_membership'] = current_subscription is not None
        context['subscriptions_history'] = subscriptions
        context['payments_history'] = payments
        context['today'] = today

        return context
