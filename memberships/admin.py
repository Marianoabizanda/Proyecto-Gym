from django.contrib import admin
from .models import Payment, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ['price']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'member',
        'plan',
        'start_date',
        'end_date',
        'status',
        'effective_status_display',
        'is_current_display',
        'days_left_display',
    )
    list_filter = ('status', 'plan', 'end_date')
    search_fields = (
        'member__username',
        'member__first_name',
        'member__last_name',
        'member__dni',
        'plan__name',
    )
    date_hierarchy = 'end_date'

    @admin.display(description='Estado actual')
    def effective_status_display(self, obj):
        return obj.effective_status

    @admin.display(boolean=True, description='¿Al día?')
    def is_current_display(self, obj):
        return obj.is_current

    @admin.display(description='Días restantes')
    def days_left_display(self, obj):
        return f"{obj.days_left} días"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_member',
        'subscription',
        'amount',
        'payment_date',
        'payment_method',
        'receipt_number',
        'registered_by',
    )
    list_filter = ('payment_method', 'payment_date')
    search_fields = (
        'subscription__member__username',
        'subscription__member__first_name',
        'subscription__member__last_name',
        'subscription__member__dni',
        'receipt_number',
        'notes',
    )
    date_hierarchy = 'payment_date'
    readonly_fields = ('created_at',)

    @admin.display(description='Socio', ordering='subscription__member')
    def get_member(self, obj):
        return obj.subscription.member
