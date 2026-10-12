from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import CustomAuthenticationForm, MemberRegistrationForm, UserProfileForm
from .models import CustomUser


class HomeRedirectView(View):
    """Redirige según el estado de la sesión."""

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return redirect('accounts:login')


class CustomLoginView(LoginView):
    """Vista de inicio de sesión con mensajes de bienvenida y redirección al dashboard."""

    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('accounts:dashboard')

    def form_valid(self, form):
        messages.success(
            self.request,
            f"¡Bienvenido/a al sistema, {form.get_user().get_full_name() or form.get_user().username}!",
        )
        return super().form_valid(form)


class CustomLogoutView(View):
    """Cierra sesión y redirige al login con notificación."""

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "Has cerrado sesión correctamente.")
        return redirect('accounts:login')

    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "Has cerrado sesión correctamente.")
        return redirect('accounts:login')


class RegisterView(CreateView):
    """Registro público exclusivo para socios."""

    model = CustomUser
    form_class = MemberRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Tu cuenta de socio fue creada con éxito. Ya puedes iniciar sesión.",
        )
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard inicial de la Fase 1: presenta el estado del usuario según su rol."""

    template_name = 'accounts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_role'] = user.role
        context['role_display'] = user.get_role_display()
        context['is_admin'] = user.is_admin_role()
        context['is_professor'] = user.is_professor_role()
        context['is_member'] = user.is_member_role()
        return context


class ProfileView(LoginRequiredMixin, UpdateView):
    """Permite al usuario autenticado visualizar y editar sus datos personales."""

    model = CustomUser
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Tus datos de perfil se actualizaron correctamente.")
        return super().form_valid(form)

