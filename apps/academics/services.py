"""
Centralized service layer for marks calculation, grading, and GPA.

This is the single authoritative source for all academic calculations.
Never trust client-provided calculated values — always recalculate here.

GPA Calculation Method:
  1. Each subject: obtained_marks / full_marks → subject percentage
  2. Subject percentage → subject grade point (using grading scale)
  3. Final GPA = average of all subject grade points
  4. Overall percentage = total_obtained / total_full * 100
  5. Overall grade is determined from overall percentage
"""

from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple

from .models import Result, SubjectMark, MarksAuditLog


# ─── Grading Scale (NEB Standard — matches user's exact table) ──────

GRADING_SCALE = [
    (90, Decimal("4.0"), "A+"),
    (80, Decimal("3.6"), "A"),
    (70, Decimal("3.2"), "B+"),
    (60, Decimal("2.8"), "B"),
    (50, Decimal("2.4"), "C+"),
    (40, Decimal("2.0"), "C"),
    (35, Decimal("1.6"), "D"),
    (0,  Decimal("0.0"), "NG"),
]

# Pass threshold: GPA >= 1.6 (i.e. at least 'D' grade overall)
PASS_GPA_THRESHOLD = Decimal("1.6")


def calculate_percentage(total_obtained: Decimal, total_full: Decimal) -> Decimal:
    """Calculate percentage from total obtained and total full marks.

    Returns Decimal rounded to 2 decimal places.
    Returns Decimal("0.00") if total_full is zero or None.
    """
    if not total_full or total_full <= 0:
        return Decimal("0.00")
    pct = (total_obtained / total_full) * Decimal("100")
    return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_grade_and_gpa(percentage: Decimal) -> Tuple[Decimal, str]:
    """Calculate grade point and letter grade from a single percentage.

    Returns (grade_point, grade) tuple.
    """
    for min_pct, gpa, grade in GRADING_SCALE:
        if percentage >= min_pct:
            return gpa, grade
    return Decimal("0.00"), "NG"


def determine_result_status(gpa: Decimal) -> str:
    """Determine PASS/FAIL/ABSENT status from GPA.

    A student passes if their GPA >= 1.6 (D grade or higher).
    """
    if gpa >= PASS_GPA_THRESHOLD:
        return "PASS"
    return "FAIL"


def calculate_result_from_subject_marks(
    subject_marks: List[dict],
) -> dict:
    """Calculate total, percentage, GPA, grade, and status from subject marks.

    GPA is calculated by averaging per-subject grade points:
      1. For each subject: percentage = obtained / full * 100
      2. Convert subject percentage → subject grade point
      3. Final GPA = sum(grade_points) / number_of_subjects

    Overall percentage is the weighted total: sum(obtained) / sum(full) * 100.
    Overall letter grade is determined from the overall percentage.

    Returns a dict with all calculated fields.
    This is the SINGLE authoritative calculation — never bypass this.
    """
    total_obtained = Decimal("0.00")
    total_full = Decimal("0.00")
    has_full_marks = False
    has_obtained_marks = False
    subject_results = []
    grade_points_sum = Decimal("0.00")
    subjects_with_both = 0  # subjects that have both full and obtained marks

    for sm in subject_marks:
        full = sm.get("full_marks")
        obt = sm.get("obtained_marks")

        if full is not None:
            total_full += Decimal(str(full))
            has_full_marks = True
        if obt is not None:
            total_obtained += Decimal(str(obt))
            has_obtained_marks = True

        # Per-subject grade point calculation
        subject_gp = Decimal("0.00")
        subject_grade = "NG"
        subject_pct = None
        if full is not None and obt is not None and full > 0:
            subject_pct = (Decimal(str(obt)) / Decimal(str(full))) * Decimal("100")
            subject_pct = subject_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subject_gp, subject_grade = calculate_grade_and_gpa(subject_pct)
            grade_points_sum += subject_gp
            subjects_with_both += 1

        subject_results.append({
            "subject": sm.get("subject", ""),
            "full_marks": full,
            "obtained_marks": obt,
            "subject_percentage": subject_pct,
            "subject_gpa": subject_gp,
            "subject_grade": subject_grade,
        })

    if not has_obtained_marks:
        return {
            "total_marks": None,
            "total_full": None,
            "percentage": None,
            "gpa": Decimal("0.00"),
            "grade": "NG",
            "result_status": "ABSENT",
            "subject_results": subject_results,
        }

    total_marks = total_obtained

    # Overall percentage (weighted by full marks)
    overall_percentage = None
    if has_full_marks and total_full > 0:
        overall_percentage = calculate_percentage(total_obtained, total_full)

    # GPA = average of per-subject grade points
    if subjects_with_both > 0:
        gpa = (grade_points_sum / Decimal(str(subjects_with_both))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        gpa = Decimal("0.00")

    # Overall grade from overall percentage
    if overall_percentage is not None:
        _, overall_grade = calculate_grade_and_gpa(overall_percentage)
    else:
        overall_grade = "-"

    # Result status from GPA
    result_status = determine_result_status(gpa)

    return {
        "total_marks": total_marks,
        "total_full": total_full,
        "percentage": overall_percentage,
        "gpa": gpa,
        "grade": overall_grade,
        "result_status": result_status,
        "subject_results": subject_results,
    }


def create_audit_log(
    result: Result,
    subject_mark: Optional[SubjectMark],
    user,
    action: str,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
    notes: str = "",
) -> MarksAuditLog:
    """Create an audit log entry for a marks change."""
    return MarksAuditLog.objects.create(
        result=result,
        subject_mark=subject_mark,
        changed_by=user,
        action=action,
        subject_name=subject_mark.subject if subject_mark else "",
        student_name=result.student_name,
        symbol_number=result.symbol_number,
        old_obtained_marks=old_data.get("obtained_marks") if old_data else None,
        new_obtained_marks=new_data.get("obtained_marks") if new_data else None,
        old_full_marks=old_data.get("full_marks") if old_data else None,
        new_full_marks=new_data.get("full_marks") if new_data else None,
        old_gpa=old_data.get("gpa") if old_data else None,
        new_gpa=new_data.get("gpa") if new_data else None,
        old_percentage=old_data.get("percentage") if old_data else None,
        new_percentage=new_data.get("percentage") if new_data else None,
        old_result_status=old_data.get("result_status") if old_data else None,
        new_result_status=new_data.get("result_status") if new_data else None,
        notes=notes,
    )


@transaction.atomic
def save_marks_and_result(
    result: Result,
    subject_marks_data: List[dict],
    user,
    notes: str = "",
) -> Result:
    """Save subject marks and recalculate the result atomically.

    This is the SINGLE entry point for saving marks. It:
    1. Deletes old subject marks (if updating)
    2. Creates new subject marks
    3. Recalculates total/percentage/GPA/grade/status
       - GPA = average of per-subject grade points
       - NOT overall-percentage-based GPA
    4. Updates the result
    5. Creates audit log entries

    Args:
        result: The Result instance to update
        subject_marks_data: List of dicts with keys:
            - subject (str)
            - full_marks (Decimal/float/str or None)
            - obtained_marks (Decimal/float/str or None)
        user: The Django User making the change
        notes: Optional notes for the audit log

    Returns:
        Updated Result instance
    """
    # Snapshot old result values for audit
    old_result_data = {
        "gpa": result.gpa,
        "percentage": result.percentage,
        "result_status": result.result_status,
    }

    # Collect old subject marks for audit comparison
    old_subject_marks = {}
    for sm in result.subject_marks.all():
        old_subject_marks[sm.subject] = {
            "id": sm.pk,
            "obtained_marks": sm.obtained_marks,
            "full_marks": sm.full_marks,
        }

    # Delete existing subject marks
    result.subject_marks.all().delete()

    # Create new subject marks
    created_marks = []
    for sm_data in subject_marks_data:
        subject_name = sm_data.get("subject", "").strip()
        if not subject_name:
            continue

        full_marks = sm_data.get("full_marks")
        obtained_marks = sm_data.get("obtained_marks")

        # Convert to Decimal if provided
        if full_marks is not None and full_marks != "":
            full_marks = Decimal(str(full_marks))
        else:
            full_marks = None

        if obtained_marks is not None and obtained_marks != "":
            obtained_marks = Decimal(str(obtained_marks))
        else:
            obtained_marks = None

        subject_mark = SubjectMark.objects.create(
            result=result,
            subject=subject_name,
            full_marks=full_marks,
            obtained_marks=obtained_marks,
        )
        created_marks.append(subject_mark)

        # Create audit log for this subject mark
        old_sm = old_subject_marks.get(subject_name)
        if old_sm:
            # Update — check if marks actually changed
            if (
                old_sm["obtained_marks"] != obtained_marks
                or old_sm["full_marks"] != full_marks
            ):
                create_audit_log(
                    result=result,
                    subject_mark=subject_mark,
                    user=user,
                    action="UPDATE",
                    old_data={
                        "obtained_marks": old_sm["obtained_marks"],
                        "full_marks": old_sm["full_marks"],
                    },
                    new_data={
                        "obtained_marks": obtained_marks,
                        "full_marks": full_marks,
                    },
                    notes=notes,
                )
        else:
            # New subject
            create_audit_log(
                result=result,
                subject_mark=subject_mark,
                user=user,
                action="CREATE",
                new_data={
                    "obtained_marks": obtained_marks,
                    "full_marks": full_marks,
                },
                notes=notes,
            )

    # Check for deleted subjects (were in old, not in new)
    new_subject_names = {sm.get("subject", "").strip() for sm in subject_marks_data}
    for old_name, old_sm_data in old_subject_marks.items():
        if old_name not in new_subject_names:
            # Subject was removed — log it
            create_audit_log(
                result=result,
                subject_mark=None,
                user=user,
                action="UPDATE",
                old_data={
                    "obtained_marks": old_sm_data["obtained_marks"],
                    "full_marks": old_sm_data["full_marks"],
                },
                notes=f"Subject '{old_name}' was removed from marks entry.",
            )

    # Recalculate result from the new subject marks
    calc_data = calculate_result_from_subject_marks(
        [
            {
                "subject": sm.subject,
                "full_marks": sm.full_marks,
                "obtained_marks": sm.obtained_marks,
            }
            for sm in created_marks
        ]
    )

    # Update result — IGNORE any client-submitted gpa/percentage/total
    result.total_marks = calc_data["total_marks"]
    result.percentage = calc_data["percentage"]
    result.gpa = calc_data["gpa"]
    result.result_status = calc_data["result_status"]
    result.save()

    # Audit log for overall result change
    new_result_data = {
        "gpa": result.gpa,
        "percentage": result.percentage,
        "result_status": result.result_status,
    }
    if old_result_data != new_result_data:
        create_audit_log(
            result=result,
            subject_mark=None,
            user=user,
            action="UPDATE" if old_result_data["gpa"] is not None else "CREATE",
            old_data=old_result_data,
            new_data=new_result_data,
            notes=notes or "Result recalculated from subject marks.",
        )

    return result
