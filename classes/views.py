from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from memberships.models import Subscription
from .forms import ActivityForm, ClassScheduleForm
from .models import Activity, ClassEnrollment, ClassSchedule


# ==============================================================================
# MIXINS DE CONTROL DE ACCESO Y PERMISOS POR ROL
# ==============================================================================

class BaseRoleRequiredMixin(AccessMixin):
    """Mixin base de permisos:
    1. Si el usuario no está autenticado, redirige al login.
    2. Si está autenticado pero carece del rol necesario, eleva 403 Forbidden (PermissionDenied).
    """

    permission_denied_message = "No tienes permisos para acceder a esta sección."

    def check_role(self, user):
        return False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.check_role(request.user):
            raise PermissionDenied(self.permission_denied_message)
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(BaseRoleRequiredMixin):
    """Acceso exclusivo para administradores del sistema."""

    permission_denied_message = "Se requieren permisos de Administrador para realizar esta acción."

    def check_role(self, user):
        return user.is_admin_role()


class ProfessorRequiredMixin(BaseRoleRequiredMixin):
    """Acceso exclusivo para profesores."""

    permission_denied_message = "Se requieren permisos de Profesor para acceder a esta sección."

    def check_role(self, user):
        return user.is_professor_role()


class StaffOrProfessorRequiredMixin(BaseRoleRequiredMixin):
    """Acceso permitido a Administradores y Profesores."""

    permission_denied_message = "Acceso restringido a Administradores y Profesores."

    def check_role(self, user):
        return user.is_admin_role() or user.is_professor_role()


class MemberRequiredMixin(BaseRoleRequiredMixin):
    """Acceso exclusivo para socios."""

    permission_denied_message = "Acceso restringido al portal de socios."

    def check_role(self, user):
        return user.is_member_role()


# ==============================================================================
# VISTAS DE ADMINISTRACIÓN (ROL ADMIN)
# ==============================================================================

class ActivityListView(AdminRequiredMixin, ListView):
    """Listado de actividades/disciplinas deportivas para gestión administrativa."""

    model = Activity
    template_name = 'classes/activity_list.html'
    context_object_name = 'activities'

    def get_queryset(self):
        return Activity.objects.all().order_by('name')


class ActivityCreateView(AdminRequiredMixin, CreateView):
    """Alta de una nueva actividad en el gimnasio."""

    model = Activity
    form_class = ActivityForm
    template_name = 'classes/activity_form.html'
    success_url = reverse_lazy('classes:activity_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"La actividad '{self.object.name}' fue creada correctamente.")
        return response


class ActivityUpdateView(AdminRequiredMixin, UpdateView):
    """Edición de una actividad existente."""

    model = Activity
    form_class = ActivityForm
    template_name = 'classes/activity_form.html'
    success_url = reverse_lazy('classes:activity_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"La actividad '{self.object.name}' fue actualizada correctamente.")
        return response


class ClassScheduleListView(AdminRequiredMixin, ListView):
    """Listado general de horarios programados en el gimnasio."""

    model = ClassSchedule
    template_name = 'classes/schedule_list.html'
    context_object_name = 'schedules'

    def get_queryset(self):
        return ClassSchedule.objects.select_related(
            'activity', 'professor'
        ).order_by('day_of_week', 'start_time')


class ClassScheduleCreateView(AdminRequiredMixin, CreateView):
    """Programación de un nuevo horario semanal."""

    model = ClassSchedule
    form_class = ClassScheduleForm
    template_name = 'classes/schedule_form.html'
    success_url = reverse_lazy('classes:schedule_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "El horario de clase fue creado correctamente.")
        return response


class ClassScheduleUpdateView(AdminRequiredMixin, UpdateView):
    """Edición de un horario semanal existente."""

    model = ClassSchedule
    form_class = ClassScheduleForm
    template_name = 'classes/schedule_form.html'
    success_url = reverse_lazy('classes:schedule_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "El horario de clase fue actualizado correctamente.")
        return response


# ==============================================================================
# VISTA DE DETALLE COMPARTIDA (ADMIN Y PROFESOR)
# ==============================================================================

class ClassScheduleDetailView(StaffOrProfessorRequiredMixin, DetailView):
    """Detalle de un horario y su lista de alumnos inscriptos.

    Aislamiento por rol:
    - El Administrador puede consultar cualquier horario del gimnasio.
    - El Profesor ÚNICAMENTE puede consultar los horarios donde él es el docente asignado.
    """

    model = ClassSchedule
    template_name = 'classes/schedule_detail.html'
    context_object_name = 'schedule'

    def get_queryset(self):
        qs = ClassSchedule.objects.select_related(
            'activity', 'professor'
        ).prefetch_related('enrollments__member')

        if self.request.user.is_admin_role():
            return qs
        # Si es profesor, restringe estrictamente a sus clases a cargo
        return qs.filter(professor=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enrollments'] = self.object.enrollments.select_related(
            'member'
        ).order_by('enrolled_at')
        return context


# ==============================================================================
# VISTAS PARA PROFESORES (ROL PROFESOR)
# ==============================================================================

class ProfessorScheduleListView(ProfessorRequiredMixin, ListView):
    """Agenda personal del profesor con sus clases asignadas."""

    model = ClassSchedule
    template_name = 'classes/professor_schedule_list.html'
    context_object_name = 'schedules'

    def get_queryset(self):
        return ClassSchedule.objects.filter(
            professor=self.request.user
        ).select_related('activity').prefetch_related('enrollments').order_by('day_of_week', 'start_time')


# ==============================================================================
# VISTAS PARA SOCIOS (ROL SOCIO)
# ==============================================================================

class AvailableScheduleListView(MemberRequiredMixin, ListView):
    """Catálogo interactivo de clases y horarios disponibles para reserva."""

    model = ClassSchedule
    template_name = 'classes/available_schedule_list.html'
    context_object_name = 'schedules'

    def get_queryset(self):
        return ClassSchedule.objects.filter(
            is_active=True,
            activity__is_active=True,
        ).select_related('activity', 'professor').prefetch_related('enrollments').order_by('day_of_week', 'start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        # Verificación de membresía vigente y acceso a clases según el plan
        active_subscription = Subscription.objects.filter(
            member=self.request.user,
            status=Subscription.Status.ACTIVA,
            start_date__lte=today,
            end_date__gte=today,
        ).select_related('plan').first()

        context['has_active_membership'] = active_subscription is not None
        context['plan_includes_classes'] = (
            active_subscription.plan.includes_classes if active_subscription else False
        )
        context['active_subscription'] = active_subscription

        # Verificación de membresía pendiente de pago
        context['pending_subscription'] = Subscription.objects.filter(
            member=self.request.user,
            status=Subscription.Status.PENDIENTE,
        ).select_related('plan').first()

        # Conjunto de IDs de horarios en los que el socio ya se encuentra inscripto
        context['enrolled_schedule_ids'] = set(
            ClassEnrollment.objects.filter(
                member=self.request.user
            ).values_list('schedule_id', flat=True)
        )
        return context


class MyEnrollmentListView(MemberRequiredMixin, ListView):
    """Listado personal de clases a las que el socio está inscripto actualmente."""

    model = ClassEnrollment
    template_name = 'classes/my_enrollment_list.html'
    context_object_name = 'enrollments'

    def get_queryset(self):
        return ClassEnrollment.objects.filter(
            member=self.request.user
        ).select_related(
            'schedule__activity', 'schedule__professor'
        ).order_by('schedule__day_of_week', 'schedule__start_time')


class EnrollClassView(MemberRequiredMixin, View):
    """Acción de inscripción de un socio a un horario de clase específico (exclusivo POST)."""

    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        schedule = get_object_or_404(
            ClassSchedule.objects.select_related('activity'),
            pk=pk
        )

        # 1. Control de estado activo de la clase y de la actividad
        if not schedule.is_active or not schedule.activity.is_active:
            messages.error(request, "Esta clase no se encuentra disponible actualmente.")
            return redirect('classes:available_schedules')

        # 2. Control de membresía vigente del socio
        today = timezone.localdate()
        active_subscription = Subscription.objects.filter(
            member=request.user,
            status=Subscription.Status.ACTIVA,
            start_date__lte=today,
            end_date__gte=today,
        ).select_related('plan').first()

        if not active_subscription:
            pending_sub = Subscription.objects.filter(
                member=request.user,
                status=Subscription.Status.PENDIENTE,
            ).first()
            if pending_sub:
                messages.warning(
                    request,
                    "Tu membresía está pendiente de activación. Esperá a que el pago sea confirmado por el gimnasio para poder inscribirte a clases."
                )
            else:
                messages.error(
                    request,
                    "Necesitás contar con una membresía activa y vigente para poder inscribirte a clases."
                )
            return redirect('classes:available_schedules')

        # 3. Control de inclusión de clases grupales en el plan contratado
        if not active_subscription.plan.includes_classes:
            messages.warning(
                request,
                f"Tu plan actual ('{active_subscription.plan.name}') no incluye clases grupales."
            )
            return redirect('classes:available_schedules')

        # 4. Control de inscripción duplicada
        if ClassEnrollment.objects.filter(schedule=schedule, member=request.user).exists():
            messages.warning(request, "Ya te encontrás inscripto en este horario.")
            return redirect('classes:available_schedules')

        # 5. Control de cupo disponible
        if schedule.is_full:
            messages.error(request, "No hay cupos disponibles para esta clase.")
            return redirect('classes:available_schedules')

        # 6. Registro exitoso de la inscripción
        ClassEnrollment.objects.create(schedule=schedule, member=request.user)
        messages.success(
            request,
            f"¡Te inscribiste exitosamente a {schedule.activity.name} ({schedule.get_day_of_week_display()})!"
        )
        return redirect('classes:my_enrollments')


class CancelEnrollmentView(MemberRequiredMixin, View):
    """Acción para que un socio cancele su propia inscripción a una clase (exclusivo POST)."""

    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        # Aislamiento estricto: solo puede cancelar inscripciones asociadas a request.user
        enrollment = get_object_or_404(
            ClassEnrollment.objects.select_related('schedule__activity'),
            pk=pk,
            member=request.user
        )

        activity_name = enrollment.schedule.activity.name
        enrollment.delete()

        messages.info(request, f"Se canceló tu inscripción a {activity_name}.")
        return redirect('classes:my_enrollments')
