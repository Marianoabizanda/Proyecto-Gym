from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

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

