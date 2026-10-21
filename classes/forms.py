from django import forms
from django.core.exceptions import ValidationError

from accounts.models import CustomUser
from .models import Activity, ClassSchedule


class ActivityForm(forms.ModelForm):
    """Formulario para la creación y edición de actividades/disciplinas del gimnasio."""

    class Meta:
        model = Activity
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Spinning, Funcional, Yoga',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción breve de la disciplina, objetivos o nivel...',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre de la actividad no puede estar vacío.')

        # Validación case-insensitive de unicidad (evita "Spinning" vs "spinning")
        qs = Activity.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe una actividad registrada con este nombre.')

        return name


class ClassScheduleForm(forms.ModelForm):
    """Formulario para programar y editar horarios de clases semanales."""

    class Meta:
        model = ClassSchedule
        fields = [
            'activity',
            'professor',
            'day_of_week',
            'start_time',
            'end_time',
            'capacity',
            'is_active',
        ]
        widgets = {
            'activity': forms.Select(attrs={
                'class': 'form-select',
            }),
            'professor': forms.Select(attrs={
                'class': 'form-select',
            }),
            'day_of_week': forms.Select(attrs={
                'class': 'form-select',
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Ej. 20',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. Filtro de Actividades: solo actividades activas.
        # Si se está editando un horario existente, se preserva su actividad actual aunque haya sido desactivada.
        activity_qs = Activity.objects.filter(is_active=True)
        if self.instance and self.instance.pk and self.instance.activity_id:
            activity_qs = activity_qs | Activity.objects.filter(pk=self.instance.activity_id)
        self.fields['activity'].queryset = activity_qs.order_by('name')
        self.fields['activity'].empty_label = 'Seleccione una actividad'

        # 2. Filtro de Profesores: usuarios con rol PROFESOR y activos en el sistema.
        # Si se está editando, se preserva al profesor actual en el queryset.
        professor_qs = CustomUser.objects.filter(role=CustomUser.Role.PROFESOR, is_active=True)
        if self.instance and self.instance.pk and self.instance.professor_id:
            professor_qs = professor_qs | CustomUser.objects.filter(pk=self.instance.professor_id)
        self.fields['professor'].queryset = professor_qs.order_by('first_name', 'last_name', 'username')
        self.fields['professor'].empty_label = 'Seleccione un profesor'

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity is not None and capacity < 1:
            raise ValidationError('El cupo máximo debe ser de al menos 1 socio.')

        # Validación de negocio en edición: no reducir el cupo por debajo de los inscriptos actuales
        if self.instance and self.instance.pk:
            enrolled = self.instance.enrolled_count
            if capacity is not None and capacity < enrolled:
                raise ValidationError(
                    f'No podés reducir el cupo a {capacity} porque ya hay {enrolled} socios inscriptos.'
                )

        return capacity

