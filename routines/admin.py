from django.contrib import admin
from .models import DailyRoutine, RoutineExercise


class RoutineExerciseInline(admin.TabularInline):
    model = RoutineExercise
    extra = 1
    fields = ('order', 'name', 'sets', 'repetitions', 'notes')
    ordering = ('order',)


@admin.register(DailyRoutine)
class DailyRoutineAdmin(admin.ModelAdmin):
    list_display = ('day_of_week', 'name', 'is_active', 'updated_at')
    list_filter = ('is_active', 'day_of_week')
    search_fields = ('name', 'description')
    inlines = [RoutineExerciseInline]


@admin.register(RoutineExercise)
class RoutineExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'routine', 'sets', 'repetitions', 'order')
    list_filter = ('routine__day_of_week', 'routine')
    search_fields = ('name', 'notes')
    ordering = ('routine', 'order')

