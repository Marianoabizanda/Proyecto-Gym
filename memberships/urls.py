from django.urls import path
from . import views

app_name = 'memberships'

urlpatterns = [
    # Planes
    path('planes/', views.PlanListView.as_view(), name='plan_list'),
    path('planes/nuevo/', views.PlanCreateView.as_view(), name='plan_create'),
    path('planes/<int:pk>/editar/', views.PlanUpdateView.as_view(), name='plan_update'),

    # Socios y Suscripciones
    path('socios/', views.MemberListView.as_view(), name='member_list'),
    path('socios/<int:pk>/', views.MemberDetailView.as_view(), name='member_detail'),
    path('suscripciones/nueva/', views.SubscriptionCreateView.as_view(), name='subscription_create'),
    path('suscripciones/<int:pk>/cancelar/', views.SubscriptionCancelView.as_view(), name='subscription_cancel'),

    # Pagos
    path('pagos/', views.PaymentListView.as_view(), name='payment_list'),
    path('pagos/registrar/', views.PaymentCreateView.as_view(), name='payment_create'),

    # Portal Socio
    path('mi-membresia/', views.MyMembershipView.as_view(), name='my_membership'),
]

