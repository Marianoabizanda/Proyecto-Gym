from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from memberships.models import Subscription
from .forms import DailyRoutineForm, RoutineExerciseForm
from .models import DailyRoutine, RoutineExercise


# ==============================================================================
# MIXINS DE CONTROL DE ACCESO
# ==============================================================================

class AdminRequiredMixin(AccessMixin):
    """Acceso exclusivo para administradores del sistema."""

    permission_denied_message = "Se requieren permisos de Administrador para realizar esta acción."

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin_role():
            raise PermissionDenied(self.permission_denied_message)
        return super().dispatch(request, *args, **kwargs)


class ActiveMemberOrAdminRequiredMixin(AccessMixin):
    """Permite el acceso a administradores o socios con membresía activa y vigente."""

    permission_denied_message = "Se requiere contar con una membresía activa para acceder a esta sección."

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_admin_role():
            return super().dispatch(request, *args, **kwargs)

        if not request.user.is_member_role():
            raise PermissionDenied("Se requiere rol de Socio para acceder a esta sección.")

        today = timezone.localdate()
        has_active_sub = Subscription.objects.filter(
            member=request.user,
            status=Subscription.Status.ACTIVA,
            start_date__lte=today,
            end_date__gte=today,
        ).exists()

        if not has_active_sub:
            messages.warning(
                request,
                "Necesitás contar con una membresía activa y vigente para consultar la rutina diaria."
            )
            return redirect('accounts:dashboard')

        return super().dispatch(request, *args, **kwargs)


# ==============================================================================
# VISTAS DE GESTIÓN DE RUTINAS (ADMIN)
# ==============================================================================

class RoutineListView(AdminRequiredMixin, ListView):
    """Listado general de rutinas diarias configuradas en el gimnasio."""

    model = DailyRoutine
    template_name = 'routines/routine_list.html'
    context_object_name = 'routines'

    def get_queryset(self):
        return DailyRoutine.objects.annotate(
            exercise_count=Count('exercises')
        ).order_by('day_of_week')


class RoutineCreateView(AdminRequiredMixin, CreateView):
    """Crea una nueva rutina diaria asignada a un día de la semana."""

    model = DailyRoutine
    form_class = DailyRoutineForm
    template_name = 'routines/routine_form.html'
    success_url = reverse_lazy('routines:routine_list')

    def form_valid(self, form):
        messages.success(self.request, "Rutina diaria creada correctamente.")
        return super().form_valid(form)


class RoutineUpdateView(AdminRequiredMixin, UpdateView):
    """Edita los datos y el estado activo/inactivo de una rutina diaria."""

    model = DailyRoutine
    form_class = DailyRoutineForm
    template_name = 'routines/routine_form.html'
    success_url = reverse_lazy('routines:routine_list')

    def form_valid(self, form):
        messages.success(self.request, "Rutina diaria actualizada correctamente.")
        return super().form_valid(form)


class RoutineDetailView(AdminRequiredMixin, DetailView):
    """Detalle de una rutina con la lista ordenada de ejercicios y opciones de administración."""

    model = DailyRoutine
    template_name = 'routines/routine_detail.html'
    context_object_name = 'routine'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exercises'] = self.object.exercises.all()
        return context


# ==============================================================================
# VISTAS DE GESTIÓN DE EJERCICIOS (ADMIN)
# ==============================================================================

class RoutineExerciseCreateView(AdminRequiredMixin, CreateView):
    """Agrega un nuevo ejercicio a una rutina diaria específica."""

    model = RoutineExercise
    form_class = RoutineExerciseForm
    template_name = 'routines/exercise_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.routine = get_object_or_404(DailyRoutine, pk=kwargs['routine_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.routine = self.routine
        messages.success(self.request, f"Ejercicio '{form.instance.name}' agregado a la rutina.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('routines:routine_detail', kwargs={'pk': self.routine.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['routine'] = self.routine
        context['is_new'] = True
        return context


class RoutineExerciseUpdateView(AdminRequiredMixin, UpdateView):
    """Edita un ejercicio existente perteneciente a una rutina."""

    model = RoutineExercise
    form_class = RoutineExerciseForm
    template_name = 'routines/exercise_form.html'

    def form_valid(self, form):
        messages.success(self.request, f"Ejercicio '{form.instance.name}' actualizado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('routines:routine_detail', kwargs={'pk': self.object.routine.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['routine'] = self.object.routine
        context['is_new'] = False
        return context


class RoutineExerciseDeleteView(AdminRequiredMixin, DeleteView):
    """Elimina un ejercicio de una rutina diaria."""

    model = RoutineExercise
    template_name = 'routines/exercise_confirm_delete.html'
    context_object_name = 'exercise'

    def get_success_url(self):
        return reverse('routines:routine_detail', kwargs={'pk': self.object.routine.pk})

    def delete(self, request, *args, **kwargs):
        exercise = self.get_object()
        messages.success(request, f"Ejercicio '{exercise.name}' eliminado de la rutina.")
        return super().delete(request, *args, **kwargs)


# ==============================================================================
# VISTA DEL SOCIO ACTIVO
# ==============================================================================

class TodayRoutineView(ActiveMemberOrAdminRequiredMixin, TemplateView):
    """Presenta al socio activo (o admin) la rutina completa programada para el día actual."""

    template_name = 'routines/today_routine.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        today_weekday = today.isoweekday()  # 1=Lunes, ..., 7=Domingo

        routine = DailyRoutine.objects.filter(
            day_of_week=today_weekday,
            is_active=True,
        ).prefetch_related('exercises').first()

        context['today'] = today
        context['today_weekday'] = today_weekday
        context['routine'] = routine
        return context

