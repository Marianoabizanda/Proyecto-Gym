from django.contrib import admin
from .models import Activity, ClassEnrollment, ClassSchedule


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ['name']


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'activity',
        'professor',
        'day_of_week',
        'start_time',
        'end_time',
        'capacity',
        'enrolled_display',
        'is_active',
    )
    list_filter = ('day_of_week', 'is_active', 'activity', 'professor')
    search_fields = (
        'activity__name',
        'professor__first_name',
        'professor__last_name',
        'professor__username',
    )
    ordering = ['day_of_week', 'start_time']

    @admin.display(description='Inscriptos / Cupo')
    def enrolled_display(self, obj):
        return f"{obj.enrolled_count} / {obj.capacity}"


@admin.register(ClassEnrollment)
class ClassEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('member', 'schedule', 'enrolled_at')
    list_filter = ('schedule__activity', 'schedule__day_of_week', 'enrolled_at')
    search_fields = (
        'member__username',
        'member__first_name',
        'member__last_name',
        'schedule__activity__name',
    )
    date_hierarchy = 'enrolled_at'
    ordering = ['-enrolled_at']
