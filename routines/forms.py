from django import forms
from .models import DailyRoutine, RoutineExercise


class DailyRoutineForm(forms.ModelForm):
    class Meta:
        model = DailyRoutine
        fields = ['day_of_week', 'name', 'description', 'is_active']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select gym-input'}),
            'name': forms.TextInput(attrs={'class': 'form-control gym-input', 'placeholder': 'Ej: Tren Superior'}),
            'description': forms.Textarea(attrs={'class': 'form-control gym-input', 'rows': 3, 'placeholder': 'Breve indicación del objetivo o grupo muscular'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input gym-check-input'}),
        }


class RoutineExerciseForm(forms.ModelForm):
    class Meta:
        model = RoutineExercise
        fields = ['name', 'sets', 'repetitions', 'notes', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control gym-input', 'placeholder': 'Ej: Press de banca plano'}),
            'sets': forms.NumberInput(attrs={'class': 'form-control gym-input', 'min': 1}),
            'repetitions': forms.TextInput(attrs={'class': 'form-control gym-input', 'placeholder': "Ej: '10', '10-12', 'Al fallo'"}),
            'notes': forms.TextInput(attrs={'class': 'form-control gym-input', 'placeholder': 'Opcional: Descanso 60s, RPE 8, etc.'}),
            'order': forms.NumberInput(attrs={'class': 'form-control gym-input', 'min': 1}),
        }

