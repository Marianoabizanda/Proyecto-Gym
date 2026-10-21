from django.urls import path
from . import views

app_name = 'classes'

urlpatterns = [
    # ==========================================================================
    # GESTIÓN DE ACTIVIDADES (ADMIN)
    # ==========================================================================
    path('actividades/', views.ActivityListView.as_view(), name='activity_list'),
    path('actividades/nueva/', views.ActivityCreateView.as_view(), name='activity_create'),
    path('actividades/<int:pk>/editar/', views.ActivityUpdateView.as_view(), name='activity_update'),

    # ==========================================================================
    # GESTIÓN DE HORARIOS (ADMIN / PROFESOR)
    # ==========================================================================
    path('horarios/', views.ClassScheduleListView.as_view(), name='schedule_list'),
    path('horarios/nuevo/', views.ClassScheduleCreateView.as_view(), name='schedule_create'),
    path('horarios/<int:pk>/editar/', views.ClassScheduleUpdateView.as_view(), name='schedule_update'),
    path('horarios/<int:pk>/', views.ClassScheduleDetailView.as_view(), name='schedule_detail'),

    # ==========================================================================
    # AGENDA DEL PROFESOR (PROFESOR)
    # ==========================================================================
    path('profesor/mis-clases/', views.ProfessorScheduleListView.as_view(), name='professor_schedules'),

    # ==========================================================================
    # PORTAL DEL SOCIO (SOCIO)
    # ==========================================================================
    path('disponibles/', views.AvailableScheduleListView.as_view(), name='available_schedules'),
    path('mis-inscripciones/', views.MyEnrollmentListView.as_view(), name='my_enrollments'),

    # Acciones transaccionales exclusivas por POST
    path('horarios/<int:pk>/inscribirme/', views.EnrollClassView.as_view(), name='enroll'),
    path('inscripciones/<int:pk>/cancelar/', views.CancelEnrollmentView.as_view(), name='cancel_enrollment'),
]

