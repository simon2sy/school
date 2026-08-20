from django import forms
from .models import Exam, ExamRoutine


class ResultSearchForm(forms.Form):
    symbol_number = forms.CharField(
        max_length=50,
        label="Symbol Number",
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your symbol number',
            'class': 'form-input',
            'autofocus': True,
        })
    )
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.filter(is_published=True).order_by('-start_date'),
        required=False,
        empty_label="All Exams",
        label="Select Exam (Optional)",
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    def clean_symbol_number(self):
        symbol = self.cleaned_data.get('symbol_number', '').strip()
        if not symbol:
            raise forms.ValidationError("Please enter a symbol number.")
        return symbol


class ExamRoutineForm(forms.ModelForm):
    """Form for creating/editing an exam routine with validation.

    * ``grade`` uses the fixed Class 1 - Class 10 choices from the model.
    * ``end_time`` must be later than ``start_time``.
    * ``exam_date`` must fall within the parent Exam's period
      (``start_date <= exam_date <= end_date``).
    """
    class Meta:
        model = ExamRoutine
        fields = [
            'exam', 'grade', 'subject',
            'exam_date', 'start_time', 'end_time',
            'room', 'remarks',
        ]
        widgets = {
            'subject': forms.TextInput(attrs={'placeholder': 'e.g., English'}),
            'room': forms.TextInput(attrs={'placeholder': 'e.g., Hall A'}),
            'remarks': forms.TextInput(attrs={'placeholder': 'Optional notes'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        exam_date = cleaned_data.get('exam_date')
        exam = cleaned_data.get('exam')

        # Validate that end_time is after start_time.
        if start_time and end_time and end_time <= start_time:
            self.add_error(
                'end_time',
                "End time must be later than the start time."
            )

        # Validate exam_date is within the parent exam's date range.
        if exam_date and exam:
            if exam.start_date and exam.end_date:
                if exam_date < exam.start_date or exam_date > exam.end_date:
                    self.add_error(
                        'exam_date',
                        f"Exam date must be within the exam period "
                        f"({exam.start_date} to {exam.end_date})."
                    )

        return cleaned_data
class ExamRoutineBulkUploadForm(forms.Form):
    file = forms.FileField(
        label="Routine File",
        help_text="Upload a CSV or Excel (.xlsx) file."
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]

        filename = uploaded_file.name.lower()

        if not filename.endswith((".csv", ".xlsx")):
            raise forms.ValidationError(
                "Only CSV and Excel (.xlsx) files are allowed."
            )

        if uploaded_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "File size cannot exceed 5 MB."
            )

        return uploaded_file