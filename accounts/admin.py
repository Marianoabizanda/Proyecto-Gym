from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, MemberProfile


class MemberProfileInline(admin.StackedInline):
    model = MemberProfile
    can_delete = False
    verbose_name = 'Ficha Médica de Socio'
    verbose_name_plural = 'Ficha Médica de Socio'
    extra = 0


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    inlines = [MemberProfileInline]

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'dni',
        'role',
        'is_staff',
        'is_superuser',
        'is_active',
    )
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'dni', 'first_name', 'last_name')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        (
            'Información adicional del Gimnasio',
            {
                'fields': ('role', 'dni', 'phone'),
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            'Información adicional del Gimnasio',
            {
                'fields': ('role', 'dni', 'phone'),
            },
        ),
    )


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'birth_date', 'medical_certificate', 'medical_certificate_date', 'emergency_contact_name', 'emergency_contact_phone')
    list_filter = ('medical_certificate',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__dni', 'emergency_contact_name')

