from django import forms
from .models import Exam


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