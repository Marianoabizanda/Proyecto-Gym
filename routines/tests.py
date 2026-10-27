import datetime
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from memberships.models import Plan, Subscription
from routines.models import DailyRoutine, RoutineExercise
from routines.views import (
    RoutineCreateView,
    RoutineDetailView,
    RoutineExerciseCreateView,
    RoutineExerciseDeleteView,
    RoutineExerciseUpdateView,
    RoutineListView,
    RoutineUpdateView,
    TodayRoutineView,
)

User = get_user_model()


class RoutineModelTests(TestCase):
    def test_daily_routine_and_exercise_creation(self):
        routine = DailyRoutine.objects.create(
            day_of_week=DailyRoutine.DayOfWeek.LUNES,
            name="Tren Superior",
            description="Pecho y Espalda",
            is_active=True,
        )
        self.assertEqual(str(routine), "Lunes — Tren Superior")

        exercise = RoutineExercise.objects.create(
            routine=routine,
            name="Press de banca",
            sets=4,
            repetitions="10-12",
            notes="RPE 8",
            order=1,
        )
        self.assertEqual(str(exercise), "Press de banca (4 x 10-12)")
        self.assertEqual(routine.exercises.count(), 1)


class RoutineSecurityAndAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(
            username='admin_test',
            password='password123',
            role=User.Role.ADMIN,
        )
        self.professor = User.objects.create_user(
            username='prof_test',
            password='password123',
            role=User.Role.PROFESOR,
        )
        self.member = User.objects.create_user(
            username='member_test',
            password='password123',
            role=User.Role.SOCIO,
        )
        self.plan = Plan.objects.create(
            name="Plan General",
            price=15000,
            duration_days=30,
            includes_classes=False,
        )
        self.routine = DailyRoutine.objects.create(
            day_of_week=timezone.localdate().isoweekday(),
            name="Rutina de Prueba",
            is_active=True,
        )
        self.exercise = RoutineExercise.objects.create(
            routine=self.routine,
            name="Sentadillas",
            sets=3,
            repetitions="10",
            order=1,
        )

    def test_routine_list_admin_allowed(self):
        req = self.factory.get(reverse('routines:routine_list'))
        req.user = self.admin
        view = RoutineListView()
        view.setup(req)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertIn('routines', context)

    def test_routine_list_non_admin_denied(self):
        req = self.factory.get(reverse('routines:routine_list'))
        req.user = self.member
        view = RoutineListView.as_view()
        with self.assertRaises(PermissionDenied):
            view(req)

        req.user = self.professor
        with self.assertRaises(PermissionDenied):
            view(req)

    def test_today_routine_inactive_member_redirects_with_warning(self):
        req = self.factory.get(reverse('routines:today_routine'))
        req.user = self.member
        req._messages = CookieStorage(req)
        view = TodayRoutineView.as_view()
        response = view(req)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:dashboard'))

    def test_today_routine_active_member_allowed(self):
        today = timezone.localdate()
        Subscription.objects.create(
            member=self.member,
            plan=self.plan,
            start_date=today - datetime.timedelta(days=2),
            end_date=today + datetime.timedelta(days=20),
            status=Subscription.Status.ACTIVA,
        )
        req = self.factory.get(reverse('routines:today_routine'))
        req.user = self.member
        req._messages = CookieStorage(req)
        view = TodayRoutineView()
        view.setup(req)
        context = view.get_context_data()
        self.assertEqual(context['routine'], self.routine)

    def test_today_routine_admin_allowed(self):
        req = self.factory.get(reverse('routines:today_routine'))
        req.user = self.admin
        view = TodayRoutineView()
        view.setup(req)
        context = view.get_context_data()
        self.assertEqual(context['routine'], self.routine)
