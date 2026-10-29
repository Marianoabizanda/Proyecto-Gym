import datetime
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from classes.models import Activity, ClassEnrollment, ClassSchedule
from classes.views import ClassScheduleDetailView, ClassScheduleListView
from memberships.models import Plan, Subscription

User = get_user_model()


class ClassOptimizationAndDetailTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(
            username='admin_classes',
            password='password123',
            role=User.Role.ADMIN,
        )
        self.prof1 = User.objects.create_user(
            username='prof1',
            password='password123',
            role=User.Role.PROFESOR,
        )
        self.prof2 = User.objects.create_user(
            username='prof2',
            password='password123',
            role=User.Role.PROFESOR,
        )
        self.member_active = User.objects.create_user(
            username='member_active',
            password='password123',
            role=User.Role.SOCIO,
        )
        self.member_inactive = User.objects.create_user(
            username='member_inactive',
            password='password123',
            role=User.Role.SOCIO,
        )

        self.activity = Activity.objects.create(
            name="Crossfit",
            description="Entrenamiento funcional de alta intensidad",
            is_active=True,
        )
        self.schedule1 = ClassSchedule.objects.create(
            activity=self.activity,
            professor=self.prof1,
            day_of_week=ClassSchedule.DayOfWeek.LUNES,
            start_time=datetime.time(18, 0),
            end_time=datetime.time(19, 0),
            capacity=15,
            is_active=True,
        )
        self.schedule2 = ClassSchedule.objects.create(
            activity=self.activity,
            professor=self.prof2,
            day_of_week=ClassSchedule.DayOfWeek.MARTES,
            start_time=datetime.time(19, 0),
            end_time=datetime.time(20, 0),
            capacity=10,
            is_active=True,
        )

        # Inscripciones
        self.enrollment_active = ClassEnrollment.objects.create(
            schedule=self.schedule1,
            member=self.member_active,
        )
        self.enrollment_inactive = ClassEnrollment.objects.create(
            schedule=self.schedule1,
            member=self.member_inactive,
        )

        # Membresía activa para member_active
        today = timezone.localdate()
        self.plan = Plan.objects.create(
            name="Plan Full",
            price=25000,
            duration_days=30,
            includes_classes=True,
            is_active=True,
        )
        Subscription.objects.create(
            member=self.member_active,
            plan=self.plan,
            start_date=today - datetime.timedelta(days=5),
            end_date=today + datetime.timedelta(days=24),
            status=Subscription.Status.ACTIVA,
        )

    def test_class_schedule_list_view_prefetches_enrollments(self):
        req = self.factory.get(reverse('classes:schedule_list'))
        req.user = self.admin
        view = ClassScheduleListView()
        view.setup(req)
        qs = view.get_queryset()

        # Verificar que prefetch_related está configurado
        self.assertTrue(any('enrollments' in str(p) for p in qs._prefetch_related_lookups))

    def test_class_schedule_detail_calculates_membership_status(self):
        req = self.factory.get(reverse('classes:schedule_detail', kwargs={'pk': self.schedule1.pk}))
        req.user = self.prof1
        view = ClassScheduleDetailView()
        view.setup(req)
        view.object = self.schedule1

        context = view.get_context_data()
        enrollments = context['enrollments']

        # Localizar las inscripciones por miembro
        enroll_active = next(e for e in enrollments if e.member == self.member_active)
        enroll_inactive = next(e for e in enrollments if e.member == self.member_inactive)

        self.assertTrue(enroll_active.has_active_membership)
        self.assertIsNotNone(enroll_active.current_subscription)

        self.assertFalse(enroll_inactive.has_active_membership)
        self.assertIsNone(enroll_inactive.current_subscription)

    def test_professor_cannot_view_other_professor_schedule(self):
        req = self.factory.get(reverse('classes:schedule_detail', kwargs={'pk': self.schedule2.pk}))
        req.user = self.prof1  # prof1 no está asignado a schedule2 (asignado a prof2)

        view = ClassScheduleDetailView.as_view()
        with self.assertRaises(Http404):
            view(req, pk=self.schedule2.pk)
