from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from .models import AcademicProgram, Exam, ExamRoutine, Result
from apps.core.models import SchoolSettings
from .forms import ResultSearchForm


def programs(request):
    """List all academic programs."""
    school = SchoolSettings.get_settings()
    program_list = AcademicProgram.objects.filter(
        is_published=True
    ).order_by('display_order')

    context = {
        'school': school,
        'programs': program_list,
        'page_title': f"Academic Programs - {school.school_name}",
        'meta_description': f"Explore academic programs offered at {school.school_name}, Birtamod, Nepal.",
    }
    return render(request, 'academics/programs.html', context)


def program_detail(request, slug):
    """Academic program detail page."""
    school = SchoolSettings.get_settings()
    program = get_object_or_404(
        AcademicProgram,
        slug=slug,
        is_published=True
    )
    other_programs = AcademicProgram.objects.filter(
        is_published=True
    ).exclude(pk=program.pk).order_by('display_order')[:4]

    context = {
        'school': school,
        'program': program,
        'other_programs': other_programs,
        'page_title': f"{program.name} - {school.school_name}",
        'meta_description': program.short_description,
    }
    return render(request, 'academics/program_detail.html', context)


def exam_routine(request):
    """Exam routine page."""
    school = SchoolSettings.get_settings()

    selected_exam_id = request.GET.get('exam')
    selected_grade = request.GET.get('grade', '')

    published_exams = Exam.objects.filter(
        is_published=True
    ).prefetch_related('routines').order_by('-start_date')

    selected_exam = None
    routines = []
    grades = []

    if published_exams.exists():
        if selected_exam_id:
            try:
                selected_exam = published_exams.get(pk=selected_exam_id)
            except Exam.DoesNotExist:
                selected_exam = published_exams.first()
        else:
            selected_exam = published_exams.first()

        if selected_exam:
            # ✅ FIX: Use a SEPARATE queryset for grades
            # Convert to a Python list to force evaluation + deduplication
            grades = list(
                ExamRoutine.objects.filter(
                    exam=selected_exam
                ).values_list(
                    'grade', flat=True
                ).distinct().order_by('grade')
            )

            # Routines queryset
            routines_qs = ExamRoutine.objects.filter(
                exam=selected_exam
            ).order_by('exam_date', 'start_time')

            if selected_grade:
                routines_qs = routines_qs.filter(grade=selected_grade)

            routines = routines_qs

    context = {
        'school': school,
        'published_exams': published_exams,
        'selected_exam': selected_exam,
        'routines': routines,
        'grades': grades,
        'selected_grade': selected_grade,
        'page_title': f"Exam Routine - {school.school_name}",
        'meta_description': f"View exam routines at {school.school_name}.",
    }
    return render(request, 'academics/exam_routine.html', context)
def results(request):
    """Result search page."""
    school = SchoolSettings.get_settings()
    form = ResultSearchForm()
    result_obj = None
    searched = False
    error_message = ""

    if request.method == 'GET' and request.GET.get('symbol_number'):
        form = ResultSearchForm(request.GET)
        searched = True

        if form.is_valid():
            symbol_number = form.cleaned_data['symbol_number']
            exam_id = form.cleaned_data.get('exam')

            try:
                query = Result.objects.filter(
                    symbol_number__iexact=symbol_number,
                    is_published=True
                ).select_related('exam')

                if exam_id:
                    query = query.filter(exam_id=exam_id)

                result_obj = query.latest('published_at')

            except Result.DoesNotExist:
                error_message = f"No published result found for symbol number '{symbol_number}'. Please verify your symbol number and try again."

    # Published exams with results
    available_exams = Exam.objects.filter(
        is_published=True,
        results__is_published=True
    ).distinct().order_by('-start_date')

    context = {
        'school': school,
        'form': form,
        'result': result_obj,
        'searched': searched,
        'error_message': error_message,
        'available_exams': available_exams,
        'page_title': f"Check Results - {school.school_name}",
        'meta_description': f"Check your exam results at {school.school_name}, Birtamod, Nepal.",
    }
    return render(request, 'academics/results.html', context)