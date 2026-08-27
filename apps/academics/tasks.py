"""
Celery tasks for academics app.

Run worker:  celery -A config worker -l info
Run beat:    celery -A config beat -l info
"""
import logging

from celery import shared_task
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ── Cache keys & TTLs ────────────────────────────────────────────────
CACHE_TTL_SHORT = 5 * 60       # 5 minutes
CACHE_TTL_MEDIUM = 30 * 60     # 30 minutes
CACHE_TTL_LONG = 6 * 60 * 60   # 6 hours


def _cache_key(key_type, *args):
    """Build a namespaced cache key."""
    parts = [str(a) for a in args if a is not None]
    return f"galaxy:{key_type}:{':'.join(parts)}"


# ── Cache warming tasks ──────────────────────────────────────────────

@shared_task(bind=True, ignore_result=True)
def warm_programs_cache(self):
    """Cache the published programs list."""
    from .models import AcademicProgram
    from apps.core.models import SchoolSettings

    school = SchoolSettings.get_settings()
    programs = list(
        AcademicProgram.objects.filter(is_published=True)
        .order_by('display_order')
        .values('id', 'name', 'slug', 'short_description', 'icon', 'duration')
    )
    cache_key = _cache_key("programs", "list")
    cache.set(cache_key, programs, CACHE_TTL_LONG)
    logger.info("Warmed programs cache (%d programs)", len(programs))


@shared_task(bind=True, ignore_result=True)
def warm_exam_routine_cache(self, exam_id, grade=None):
    """Cache filtered exam routines for a given exam (+ optional grade)."""
    from .models import ExamRoutine

    grade_label_map = dict(ExamRoutine.GRADE_CHOICES)
    grade_order = [v for v, _ in ExamRoutine.GRADE_CHOICES]

    qs = ExamRoutine.objects.filter(exam_id=exam_id).order_by(
        'grade', 'exam_date', 'start_time'
    )
    if grade:
        qs = qs.filter(grade=grade)

    graded = {v: [] for v in grade_order}
    for r in qs:
        graded.setdefault(r.grade, []).append(r)

    class_routines = [
        {
            'grade': v,
            'grade_label': grade_label_map.get(v, v),
            'routines': [
                {
                    'subject': routine.subject,
                    'exam_date': routine.exam_date.isoformat(),
                    'start_time': routine.start_time.strftime('%H:%M'),
                    'end_time': routine.end_time.strftime('%H:%M'),
                    'room': routine.room,
                    'remarks': routine.remarks,
                }
                for routine in graded[v]
            ],
        }
        for v in grade_order
        if graded.get(v)
    ]

    cache_key = _cache_key("routine", exam_id, grade or "all")
    cache.set(cache_key, class_routines, CACHE_TTL_MEDIUM)
    logger.info("Warmed routine cache for exam=%s grade=%s", exam_id, grade)


@shared_task(bind=True, ignore_result=True)
def warm_result_cache(self, symbol_number, exam_id=None):
    """Cache a single result lookup (for the public results page)."""
    from .models import Result

    try:
        query = Result.objects.filter(
            symbol_number__iexact=symbol_number,
            is_published=True,
        ).select_related('exam').prefetch_related('subject_marks')

        if exam_id:
            query = query.filter(exam_id=exam_id)

        result_obj = query.latest('published_at')

        result_data = {
            'student_name': result_obj.student_name,
            'symbol_number': result_obj.symbol_number,
            'grade': result_obj.grade,
            'roll_number': result_obj.roll_number,
            'total_marks': str(result_obj.total_marks) if result_obj.total_marks else None,
            'percentage': str(result_obj.percentage) if result_obj.percentage else None,
            'gpa': str(result_obj.gpa) if result_obj.gpa else None,
            'result_status': result_obj.result_status,
            'exam_name': result_obj.exam.name if result_obj.exam else None,
            'subject_marks': [
                {
                    'subject': sm.subject,
                    'full_marks': str(sm.full_marks) if sm.full_marks else None,
                    'obtained_marks': str(sm.obtained_marks) if sm.obtained_marks else None,
                }
                for sm in result_obj.subject_marks.all()
            ],
        }

        cache_key = _cache_key("result", symbol_number, str(exam_id or "latest"))
        cache.set(cache_key, result_data, CACHE_TTL_SHORT)
        logger.info("Warmed result cache for symbol=%s", symbol_number)

    except Result.DoesNotExist:
        logger.debug("No result found for symbol=%s — skipping cache", symbol_number)


# ── Cache invalidation tasks ─────────────────────────────────────────

@shared_task(bind=True, ignore_result=True)
def invalidate_program_caches(self):
    """Invalidate all program-related caches."""
    cache.delete(_cache_key("programs", "list"))
    logger.info("Invalidated programs cache")


@shared_task(bind=True, ignore_result=True)
def invalidate_routine_caches(self, exam_id=None):
    """Invalidate routine caches for a given exam (or all)."""
    if exam_id:
        cache.delete(_cache_key("routine", exam_id, "all"))
        from .models import ExamRoutine
        for grade_value, _ in ExamRoutine.GRADE_CHOICES:
            cache.delete(_cache_key("routine", exam_id, grade_value))
    logger.info("Invalidated routine caches for exam=%s", exam_id)


@shared_task(bind=True, ignore_result=True)
def invalidate_result_cache(self, symbol_number, exam_id=None):
    """Invalidate result cache when a result is created/edited."""
    cache.delete(_cache_key("result", symbol_number, str(exam_id or "latest")))
    cache.delete(_cache_key("result", symbol_number, "latest"))
    logger.info("Invalidated result cache for symbol=%s", symbol_number)


# ── Bulk processing tasks ────────────────────────────────────────────

@shared_task(bind=True, ignore_result=False, max_retries=3)
def bulk_recalculate_all_gpas(self, exam_id):
    """Recalculate GPA/percentage/status for all results of an exam.

    Useful when the grading scale changes.
    """
    from .models import Result, SubjectMark
    from .services import calculate_result_from_subject_marks

    results = Result.objects.filter(exam_id=exam_id).prefetch_related('subject_marks')
    updated = 0
    errors = []

    for result in results:
        try:
            subject_data = [
                {
                    'subject': sm.subject,
                    'full_marks': float(sm.full_marks) if sm.full_marks else 100.0,
                    'obtained_marks': float(sm.obtained_marks) if sm.obtained_marks else 0.0,
                }
                for sm in result.subject_marks.all()
            ]

            if not subject_data:
                continue

            calc = calculate_result_from_subject_marks(subject_data)

            with transaction.atomic():
                result.total_marks = calc['total_obtained']
                result.percentage = calc['percentage']
                result.gpa = calc['gpa']
                result.result_status = calc['result_status']
                result.save(update_fields=[
                    'total_marks', 'percentage', 'gpa',
                    'result_status', 'updated_at',
                ])

            # Invalidate this student's result cache
            invalidate_result_cache.delay(result.symbol_number, exam_id)
            updated += 1

        except Exception as e:
            errors.append(f"Result {result.pk} ({result.symbol_number}): {e}")
            logger.error("Failed to recalculate result %s: %s", result.pk, e)

    logger.info(
        "Bulk GPA recalculation for exam=%s: %d updated, %d errors",
        exam_id, updated, len(errors),
    )
    return {
        'exam_id': exam_id,
        'updated': updated,
        'errors': errors,
    }


@shared_task(bind=True, ignore_result=False, max_retries=2)
def send_result_notifications(self, exam_id):
    """Send email notifications to students/parents after results are published.

    This is a placeholder — adapt the email template to your school's needs.
    """
    from .models import Result

    results = Result.objects.filter(
        exam_id=exam_id,
        is_published=True,
    ).select_related('exam')

    sent = 0
    for result in results:
        # Placeholder: In production, look up parent email and send
        # For now, just log that we would send
        logger.info(
            "Notification would be sent: %s (%s) — GPA: %s, Status: %s",
            result.student_name,
            result.symbol_number,
            result.gpa,
            result.result_status,
        )
        sent += 1

    logger.info("Result notifications for exam=%s: %d students", exam_id, sent)
    return {'exam_id': exam_id, 'notified': sent}


@shared_task(bind=True, ignore_result=True)
def warm_all_public_caches(self):
    """Warm all public-facing caches. Run periodically via Celery Beat."""
    from .models import Exam

    # Warm programs
    warm_programs_cache.delay()

    # Warm routines for the latest published exam
    latest_exam = Exam.objects.filter(is_published=True).order_by('-start_date').first()
    if latest_exam:
        warm_exam_routine_cache.delay(latest_exam.id)
        from .models import ExamRoutine
        for grade_value, _ in ExamRoutine.GRADE_CHOICES:
            warm_exam_routine_cache.delay(latest_exam.id, grade_value)

    logger.info("Warmed all public caches")
