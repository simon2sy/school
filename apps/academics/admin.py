from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import (
    AcademicProgram, Exam, ExamRoutine, Result, SubjectMark,
    TeacherSubjectAssignment, MarksAuditLog,
)

from .views import bulk_upload_exam_routine


# ── Cache invalidation signals ──────────────────────────────────────
# When models change via Django admin (or any ORM save/delete),
# invalidate the relevant caches immediately.

@receiver(post_save, sender=AcademicProgram)
@receiver(post_delete, sender=AcademicProgram)
def _invalidate_program_cache(sender, **kwargs):
    cache.delete('galaxy:programs:list')
    try:
        from .tasks import invalidate_program_caches
        invalidate_program_caches.delay()
    except Exception:
        pass


@receiver(post_save, sender=ExamRoutine)
@receiver(post_delete, sender=ExamRoutine)
def _invalidate_routine_cache(sender, instance, **kwargs):
    cache.delete(f'galaxy:routine:{instance.exam_id}:all')
    cache.delete(f'galaxy:routine:{instance.exam_id}:{instance.grade}')
    try:
        from .tasks import invalidate_routine_caches
        invalidate_routine_caches.delay(instance.exam_id)
    except Exception:
        pass


@receiver(post_save, sender=Result)
@receiver(post_delete, sender=Result)
def _invalidate_result_cache(sender, instance, **kwargs):
    cache.delete(f'galaxy:result:{instance.symbol_number}:latest')
    cache.delete(f'galaxy:result:{instance.symbol_number}:{instance.exam_id}')
    try:
        from .tasks import invalidate_result_cache
        invalidate_result_cache.delay(instance.symbol_number, instance.exam_id)
    except Exception:
        pass
class ExamRoutineInline(admin.TabularInline):
    """Inline to add exam routines directly while editing an examination."""
    model = ExamRoutine
    extra = 1
    fields = ('grade', 'subject', 'exam_date',
              'start_time', 'end_time', 'room', 'remarks')


@admin.register(AcademicProgram)
class AcademicProgramAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'duration', 'display_order',
        'is_published', 'updated_at'
    ]
    list_filter = ['is_published']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order', 'name']
    list_editable = ['display_order', 'is_published']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'short_description', 'description')
        }),
        ('Details', {
            'fields': ('duration', 'eligibility', 'icon', 'featured_image')
        }),
        ('Display', {
            'fields': ('is_published', 'display_order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):

    change_form_template = "academics/exam/change_form.html"

    list_display = [
        'name', 'academic_year',
        'start_date', 'end_date', 'is_published'
    ]

    list_filter = [
        'academic_year',
        'is_published'
    ]

    search_fields = [
        'name',
        'academic_year'
    ]

    ordering = ['-start_date']

    list_editable = ['is_published']

    readonly_fields = [
        'created_at',
        'updated_at'
    ]

    inlines = [ExamRoutineInline]

    fieldsets = (
        ('Examination', {
            'fields': (
                'name',
                'academic_year'
            )
        }),

        ('Dates', {
            'fields': (
                'start_date',
                'end_date'
            )
        }),

        ('Publication', {
            'fields': (
                'is_published',
            )
        }),

        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',),
        }),
    )

    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [
            path(
                '<int:exam_id>/bulk-upload-routine/',
                self.admin_site.admin_view(
                    bulk_upload_exam_routine
                ),
                name='academics_exam_bulk_upload_routine',
            ),
        ]

        return custom_urls + urls


@admin.register(ExamRoutine)
class ExamRoutineAdmin(admin.ModelAdmin):
    list_display = [
        'exam', 'grade', 'subject',
        'exam_date', 'start_time', 'end_time', 'room'
    ]
    list_filter = ['exam', 'grade', 'exam_date']
    search_fields = ['subject', 'grade', 'exam__name']
    ordering = ['grade', 'exam_date', 'start_time']
    autocomplete_fields = ['exam']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'exam_date'


class ResultSubjectMarkInline(admin.TabularInline):
    """Inline to enter each subject's marks that make up a result."""
    model = SubjectMark
    extra = 1
    fields = ('subject', 'full_marks', 'obtained_marks')


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = [
        'student_name', 'symbol_number', 'exam',
        'grade', 'percentage', 'gpa',
        'result_status_badge', 'is_published'
    ]
    list_filter = [
        'result_status', 'is_published', 'exam', 'grade'
    ]
    search_fields = ['student_name', 'symbol_number', 'roll_number']
    ordering = ['-published_at']
    list_editable = ['is_published']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['exam']
    date_hierarchy = 'published_at'
    inlines = [ResultSubjectMarkInline]

    fieldsets = (
        ('Student Information', {
            'fields': (
                'student_name', 'symbol_number',
                'roll_number', 'grade', 'exam'
            )
        }),
        ('Result', {
            'fields': (
                'total_marks', 'percentage',
                'gpa', 'result_status'
            )
        }),
        ('Publication', {
            'fields': ('is_published', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def result_status_badge(self, obj):
        colors = {
            'PASS': '#16a34a',
            'FAIL': '#dc2626',
            'ABSENT': '#d97706',
        }
        color = colors.get(obj.result_status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_result_status_display()
        )
    result_status_badge.short_description = 'Status'


@admin.register(TeacherSubjectAssignment)
class TeacherSubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'grade', 'subject', 'created_at']
    list_filter = ['grade', 'user']
    search_fields = ['user__username', 'subject']
    autocomplete_fields = ['user']
    ordering = ['grade', 'subject', 'user']
    readonly_fields = ['created_at']


@admin.register(MarksAuditLog)
class MarksAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'action', 'changed_by',
        'student_name', 'symbol_number', 'subject_name',
        'old_obtained_marks', 'new_obtained_marks',
    ]
    list_filter = ['action', 'created_at', 'changed_by']
    search_fields = [
        'student_name', 'symbol_number', 'subject_name',
        'changed_by__username',
    ]
    readonly_fields = [
        'result', 'subject_mark', 'changed_by', 'action',
        'old_obtained_marks', 'new_obtained_marks',
        'old_full_marks', 'new_full_marks',
        'old_gpa', 'new_gpa', 'old_percentage', 'new_percentage',
        'old_result_status', 'new_result_status',
        'subject_name', 'student_name', 'symbol_number',
        'notes', 'created_at',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False  # Audit logs are created by the system, not manually

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable

    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs cannot be deleted