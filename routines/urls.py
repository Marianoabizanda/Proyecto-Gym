from django.urls import path
from . import views

app_name = 'routines'

urlpatterns = [
    # Gestión de Rutinas (ADMIN)
    path('', views.RoutineListView.as_view(), name='routine_list'),
    path('crear/', views.RoutineCreateView.as_view(), name='routine_create'),
    path('hoy/', views.TodayRoutineView.as_view(), name='today_routine'),
    path('<int:pk>/', views.RoutineDetailView.as_view(), name='routine_detail'),
    path('<int:pk>/editar/', views.RoutineUpdateView.as_view(), name='routine_update'),

    # Gestión de Ejercicios (ADMIN)
    path('<int:routine_id>/ejercicios/agregar/', views.RoutineExerciseCreateView.as_view(), name='exercise_create'),
    path('ejercicios/<int:pk>/editar/', views.RoutineExerciseUpdateView.as_view(), name='exercise_update'),
    path('ejercicios/<int:pk>/eliminar/', views.RoutineExerciseDeleteView.as_view(), name='exercise_delete'),
]

