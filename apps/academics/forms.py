from django import forms
from decimal import Decimal, InvalidOperation
from .models import Exam, ExamRoutine, Result, SubjectMark


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


class SubjectMarkForm(forms.Form):
    """Form for a single subject's marks entry."""
    subject = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Mathematics',
            'class': 'w-full text-base px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
        }),
    )
    full_marks = forms.DecimalField(
        max_digits=6, decimal_places=2,
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'placeholder': '100',
            'step': 'any',
            'min': '0',
            'class': 'w-full text-sm px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
        }),
    )
    obtained_marks = forms.DecimalField(
        max_digits=6, decimal_places=2,
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'placeholder': '85',
            'step': 'any',
            'min': '0',
            'class': 'w-full text-sm px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get('subject', '').strip()
        full_marks = cleaned_data.get('full_marks')
        obtained_marks = cleaned_data.get('obtained_marks')

        # Skip completely empty rows
        if not subject and full_marks is None and obtained_marks is None:
            return cleaned_data

        if not subject:
            self.add_error('subject', 'Subject name is required.')

        if obtained_marks is not None and full_marks is not None:
            if full_marks > 0 and obtained_marks > full_marks:
                self.add_error(
                    'obtained_marks',
                    f'Obtained marks ({obtained_marks}) cannot exceed '
                    f'full marks ({full_marks}).'
                )

        return cleaned_data


class ResultForm(forms.ModelForm):
    """Form for creating/editing a result (student info only — marks are separate)."""
    class Meta:
        model = Result
        fields = [
            'exam', 'student_name', 'symbol_number',
            'grade', 'roll_number', 'result_status',
        ]
        widgets = {
            'exam': forms.Select(attrs={
                'class': 'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            }),
            'student_name': forms.TextInput(attrs={
                'placeholder': 'Full name as on the certificate',
                'class': 'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            }),
            'symbol_number': forms.TextInput(attrs={
                'placeholder': 'e.g., GES-2024-001',
                'class': 'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            }),
            'grade': forms.Select(attrs={
                'class': 'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            }),
            'roll_number': forms.TextInput(attrs={
                'placeholder': 'Optional',
                'class': 'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            }),
            'result_status': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        self.requesting_user = kwargs.pop('requesting_user', None)
        super().__init__(*args, **kwargs)
        self.fields['grade'].choices = ExamRoutine.GRADE_CHOICES
        self.fields['roll_number'].required = False
        self.fields['result_status'].required = False

    def clean_symbol_number(self):
        symbol = self.cleaned_data.get('symbol_number', '').strip()
        if not symbol:
            raise forms.ValidationError('Symbol number is required.')
        return symbol

    def clean_student_name(self):
        name = self.cleaned_data.get('student_name', '').strip()
        if not name:
            raise forms.ValidationError('Student name is required.')
        return name

class ResultEditForm(forms.Form):
    """Form for editing an existing result — validates permissions server-side."""
    student_name = forms.CharField(max_length=200)
    symbol_number = forms.CharField(max_length=50)
    grade = forms.ChoiceField(choices=ExamRoutine.GRADE_CHOICES)
    roll_number = forms.CharField(max_length=50, required=False)
    result_status = forms.ChoiceField(
        choices=Result.RESULT_STATUS_CHOICES,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.result = kwargs.pop('result', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.result:
            # Symbol number must be unique per exam (excluding current result)
            symbol = cleaned_data.get('symbol_number', '').strip()
            grade = cleaned_data.get('grade')
            if symbol and grade:
                dup = Result.objects.filter(
                    exam=self.result.exam,
                    symbol_number__iexact=symbol,
                ).exclude(pk=self.result.pk)
                if dup.exists():
                    raise forms.ValidationError(
                        f'A result for symbol number \'{symbol}\' already exists '
                        f'for this exam.'
                    )
        return cleaned_data