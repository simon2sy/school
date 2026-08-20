from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from .models import AcademicProgram, Exam, ExamRoutine, Result

from .views import bulk_upload_exam_routine
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