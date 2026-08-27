"""
Permission checks for marks entry and result management.

Every check is server-side. Never trust client-submitted IDs or roles.
"""

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.http import HttpRequest
from typing import Optional, Tuple

from .models import (
    Exam, Result, SubjectMark,
    TeacherSubjectAssignment, ExamRoutine,
)


def can_enter_marks(user: User) -> bool:
    """Check if user is authenticated and has staff privileges."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def get_teacher_assignments(user: User):
    """Get all subject assignments for a teacher."""
    return TeacherSubjectAssignment.objects.filter(user=user)


def is_teacher_assigned_to_subject(
    user: User,
    grade: str,
    subject: str,
) -> bool:
    """Check if a teacher is authorized to enter marks for a specific class + subject.

    Superusers are always authorized.
    """
    if user.is_superuser:
        return True
    return TeacherSubjectAssignment.objects.filter(
        user=user,
        grade=grade,
        subject__iexact=subject.strip(),
    ).exists()


def is_teacher_assigned_to_grade(user: User, grade: str) -> bool:
    """Check if a teacher is assigned to any subject in a given class.

    Superusers are always authorized.
    """
    if user.is_superuser:
        return True
    return TeacherSubjectAssignment.objects.filter(
        user=user,
        grade=grade,
    ).exists()


def get_authorized_subjects(user: User, grade: str) -> list:
    """Get list of subjects a teacher is authorized for in a given class."""
    if user.is_superuser:
        # Return all subjects from exam routines for this grade
        return list(
            ExamRoutine.objects.filter(grade=grade)
            .values_list("subject", flat=True)
            .distinct()
        )
    return list(
        TeacherSubjectAssignment.objects.filter(
            user=user, grade=grade
        ).values_list("subject", flat=True)
    )


def can_edit_result(user: User, result: Result) -> bool:
    """Check if a user can edit a specific result.

    - Superusers can always edit
    - Staff users can edit results in their assigned grades
    """
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    return is_teacher_assigned_to_grade(user, result.grade)


def validate_exam_exists(exam_id) -> Tuple[Optional[Exam], Optional[str]]:
    """Validate that an exam exists and return it or an error message."""
    try:
        exam = Exam.objects.get(pk=exam_id)
        return exam, None
    except Exam.DoesNotExist:
        return None, "Invalid exam selected."


def validate_grade(grade: str) -> Tuple[bool, Optional[str]]:
    """Validate that a grade is valid."""
    valid_grades = dict(ExamRoutine.GRADE_CHOICES)
    if grade not in valid_grades:
        return False, "Please choose a valid class."
    return True, None


def validate_marks_range(
    obtained: Optional[float],
    full: Optional[float],
    subject_name: str,
) -> Optional[str]:
    """Validate marks are within valid range.

    Returns error message if invalid, None if valid.
    """
    if obtained is not None and obtained < 0:
        return f"Marks for '{subject_name}' cannot be negative."

    if full is not None and full < 0:
        return f"Full marks for '{subject_name}' cannot be negative."

    if obtained is not None and full is not None and full > 0 and obtained > full:
        return (
            f"Marks obtained ({obtained}) for '{subject_name}' "
            f"cannot exceed full marks ({full})."
        )

    return None


def validate_subject_mark_data(
    subjects: list,
    full_marks_list: list,
    obtained_marks_list: list,
) -> Tuple[list, list]:
    """Validate all subject mark data and return (cleaned_data, errors).

    cleaned_data is a list of dicts suitable for the service layer.
    """
    cleaned = []
    errors = []

    for i, subject in enumerate(subjects):
        subject = subject.strip() if subject else ""
        if not subject:
            continue

        full_marks = None
        obtained_marks = None

        # Parse full marks
        if i < len(full_marks_list) and full_marks_list[i].strip():
            try:
                full_marks = float(full_marks_list[i])
            except (ValueError, TypeError):
                errors.append(
                    f"Full marks for '{subject}' must be a valid number."
                )
                continue

        # Parse obtained marks
        if i < len(obtained_marks_list) and obtained_marks_list[i].strip():
            try:
                obtained_marks = float(obtained_marks_list[i])
            except (ValueError, TypeError):
                errors.append(
                    f"Obtained marks for '{subject}' must be a valid number."
                )
                continue

        # Validate range
        range_error = validate_marks_range(obtained_marks, full_marks, subject)
        if range_error:
            errors.append(range_error)
            continue

        cleaned.append({
            "subject": subject,
            "full_marks": full_marks,
            "obtained_marks": obtained_marks,
        })

    return cleaned, errors
