import datetime
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from memberships.models import Payment, Plan, Subscription
from memberships.views import MemberCancelPendingSubscriptionView, MemberSelectPlanView

User = get_user_model()


class MemberCancelPendingSubscriptionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.member = User.objects.create_user(
            username='member_cancel',
            password='password123',
            role=User.Role.SOCIO,
        )
        self.other_member = User.objects.create_user(
            username='other_member',
            password='password123',
            role=User.Role.SOCIO,
        )
        self.admin = User.objects.create_user(
            username='admin_cancel',
            password='password123',
            role=User.Role.ADMIN,
        )
        self.plan1 = Plan.objects.create(
            name="Plan Inicial",
            price=12000,
            duration_days=30,
            is_active=True,
        )
        self.plan2 = Plan.objects.create(
            name="Plan Definitivo",
            price=20000,
            duration_days=30,
            is_active=True,
        )
        self.sub_pending = Subscription.objects.create(
            member=self.member,
            plan=self.plan1,
            start_date=timezone.localdate(),
            status=Subscription.Status.PENDIENTE,
        )

    def test_cancel_pending_subscription_success(self):
        req = self.factory.post(
            reverse('memberships:cancel_pending_subscription', kwargs={'pk': self.sub_pending.pk})
        )
        req.user = self.member
        req._messages = CookieStorage(req)

        view = MemberCancelPendingSubscriptionView.as_view()
        response = view(req, pk=self.sub_pending.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('memberships:my_membership'))

        self.sub_pending.refresh_from_db()
        self.assertEqual(self.sub_pending.status, Subscription.Status.CANCELADA)

    def test_can_select_new_plan_after_cancellation(self):
        # 1. Cancelar la solicitud pendiente
        self.sub_pending.status = Subscription.Status.CANCELADA
        self.sub_pending.save(update_fields=['status'])

        # 2. Intentar seleccionar otro plan
        req = self.factory.post(
            reverse('memberships:select_plan', kwargs={'pk': self.plan2.pk})
        )
        req.user = self.member
        req._messages = CookieStorage(req)

        view = MemberSelectPlanView.as_view()
        response = view(req, pk=self.plan2.pk)

        self.assertEqual(response.status_code, 302)
        new_pending = Subscription.objects.filter(
            member=self.member,
            status=Subscription.Status.PENDIENTE,
        ).first()
        self.assertIsNotNone(new_pending)
        self.assertEqual(new_pending.plan, self.plan2)

    def test_cancel_other_member_subscription_forbidden(self):
        req = self.factory.post(
            reverse('memberships:cancel_pending_subscription', kwargs={'pk': self.sub_pending.pk})
        )
        req.user = self.other_member
        req._messages = CookieStorage(req)

        view = MemberCancelPendingSubscriptionView.as_view()
        with self.assertRaises(Http404):
            view(req, pk=self.sub_pending.pk)

    def test_cannot_cancel_active_subscription(self):
        today = timezone.localdate()
        active_sub = Subscription.objects.create(
            member=self.member,
            plan=self.plan1,
            start_date=today,
            end_date=today + datetime.timedelta(days=29),
            status=Subscription.Status.ACTIVA,
        )
        req = self.factory.post(
            reverse('memberships:cancel_pending_subscription', kwargs={'pk': active_sub.pk})
        )
        req.user = self.member
        req._messages = CookieStorage(req)

        view = MemberCancelPendingSubscriptionView.as_view()
        response = view(req, pk=active_sub.pk)

        self.assertEqual(response.status_code, 302)
        active_sub.refresh_from_db()
        self.assertEqual(active_sub.status, Subscription.Status.ACTIVA)

    def test_cannot_cancel_with_existing_payments(self):
        Payment.objects.create(
            subscription=self.sub_pending,
            amount=self.plan1.price,
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.EFECTIVO,
            registered_by=self.admin,
        )
        req = self.factory.post(
            reverse('memberships:cancel_pending_subscription', kwargs={'pk': self.sub_pending.pk})
        )
        req.user = self.member
        req._messages = CookieStorage(req)

        view = MemberCancelPendingSubscriptionView.as_view()
        response = view(req, pk=self.sub_pending.pk)

        self.assertEqual(response.status_code, 302)
        self.sub_pending.refresh_from_db()
        self.assertEqual(self.sub_pending.status, Subscription.Status.PENDIENTE)

    def test_get_method_not_allowed(self):
        req = self.factory.get(
            reverse('memberships:cancel_pending_subscription', kwargs={'pk': self.sub_pending.pk})
        )
        req.user = self.member
        view = MemberCancelPendingSubscriptionView.as_view()
        response = view(req, pk=self.sub_pending.pk)
        self.assertEqual(response.status_code, 405)

