from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid
from apps.core.image_utils import optimize_image, image_field_unchanged


class AcademicProgram(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    short_description = models.CharField(
        max_length=300,
        help_text="Brief description shown in cards"
    )
    description = models.TextField(
        help_text="Full program description"
    )
    featured_image = models.ImageField(
        upload_to='academics/programs/',
        null=True, blank=True
    )
    duration = models.CharField(
        max_length=100,
        help_text="e.g., 2 Years",
        blank=True
    )
    eligibility = models.TextField(
        help_text="Eligibility criteria for this program",
        blank=True
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Heroicon name (e.g., academic-cap)"
    )
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower number appears first"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Academic Program"
        verbose_name_plural = "Academic Programs"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        if not image_field_unchanged(self, 'featured_image'):
            optimize_image(self.featured_image)
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1
        while AcademicProgram.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('academics:program_detail', kwargs={'slug': self.slug})


class Exam(models.Model):
    name = models.CharField(
        max_length=200,
        help_text="e.g., First Terminal Examination 2083"
    )
    academic_year = models.CharField(
        max_length=20,
        help_text="e.g., 2083/84"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Exam"
        verbose_name_plural = "Exams"
        indexes = [
            models.Index(fields=['-start_date']),
            models.Index(fields=['academic_year']),
        ]

    def __str__(self):
        return f"{self.name} - {self.academic_year}"


class ExamRoutine(models.Model):
    GRADE_CHOICES = [
        ('1', 'Class 1'),
        ('2', 'Class 2'),
        ('3', 'Class 3'),
        ('4', 'Class 4'),
        ('5', 'Class 5'),
        ('6', 'Class 6'),
        ('7', 'Class 7'),
        ('8', 'Class 8'),
        ('9', 'Class 9'),
        ('10', 'Class 10'),
    ]

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='routines'
    )
    grade = models.CharField(
        max_length=2,
        choices=GRADE_CHOICES,
        verbose_name="Class",
        help_text="Select the class (Class 1 - Class 10)"
    )
    subject = models.CharField(max_length=200)
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(
        max_length=100,
        blank=True,
        help_text="Exam room or hall"
    )
    remarks = models.CharField(
        max_length=300,
        blank=True,
        help_text="Additional notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['grade', 'exam_date', 'start_time']

        verbose_name = "Exam Routine"
        verbose_name_plural = "Exam Routines"

        indexes = [
            models.Index(fields=['exam_date']),
            models.Index(fields=['exam', 'grade']),
            models.Index(fields=['grade']),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'exam',
                    'grade',
                    'subject',
                    'exam_date',
                    'start_time',
                ],
                name='unique_exam_routine',
            ),
        ]

    def __str__(self):
        return f"{self.exam} - {self.subject} ({self.exam_date})"


class Result(models.Model):
    RESULT_STATUS_CHOICES = [
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
        ('ABSENT', 'Absent'),
    ]

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='results'
    )
    student_name = models.CharField(max_length=200)
    symbol_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Unique symbol number for result lookup"
    )
    grade = models.CharField(max_length=50, db_index=True)
    roll_number = models.CharField(max_length=50, blank=True)
    total_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True, blank=True
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True, blank=True
    )
    gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True, blank=True
    )
    result_status = models.CharField(
        max_length=10,
        choices=RESULT_STATUS_CHOICES,
        default='PASS'
    )
    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = "Result"
        verbose_name_plural = "Results"
        indexes = [
            models.Index(fields=['symbol_number']),
            models.Index(fields=['exam', 'grade']),
            models.Index(fields=['is_published']),
        ]
        unique_together = [['exam', 'symbol_number']]

    def __str__(self):
        return f"{self.student_name} ({self.symbol_number}) - {self.exam}"

    def get_status_color(self):
        colors = {
            'PASS': 'green',
            'FAIL': 'red',
            'ABSENT': 'yellow',
        }
        return colors.get(self.result_status, 'gray')


class SubjectMark(models.Model):
    """Marks obtained by a student for an individual subject in an exam.

    Each row ties one subject to a published result, so the result card can
    show subject-wise marks instead of only the overall total.
    """
    result = models.ForeignKey(
        Result,
        on_delete=models.CASCADE,
        related_name='subject_marks',
        help_text="The result (student/exam) these subject marks belong to"
    )
    subject = models.CharField(
        max_length=200,
        help_text="e.g., English, Mathematics, Science"
    )
    full_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum marks for this subject (optional)"
    )
    obtained_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Marks obtained by the student in this subject"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subject']
        verbose_name = "Subject Mark"
        verbose_name_plural = "Subject Marks"
        constraints = [
            models.UniqueConstraint(
                fields=['result', 'subject'],
                name='unique_result_subject_mark',
            ),
        ]

    def __str__(self):
        return f"{self.subject}: {self.obtained_marks}"


class TeacherSubjectAssignment(models.Model):
    """Maps a teacher (User) to the classes and subjects they are authorized to enter marks for.

    A teacher assigned to Class 9 Mathematics can only enter marks for
    Class 9 Mathematics — never for another class or subject.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subject_assignments',
        help_text="The teacher (Django user)"
    )
    grade = models.CharField(
        max_length=2,
        choices=ExamRoutine.GRADE_CHOICES,
        help_text="Class the teacher is assigned to"
    )
    subject = models.CharField(
        max_length=200,
        help_text="Subject the teacher is authorized for"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Teacher Subject Assignment"
        verbose_name_plural = "Teacher Subject Assignments"
        unique_together = [['user', 'grade', 'subject']]
        indexes = [
            models.Index(fields=['user', 'grade']),
        ]

    def __str__(self):
        return f"{self.user.username} → Class {self.grade} - {self.subject}"


class MarksAuditLog(models.Model):
    """Immutable audit trail for every marks modification.

    Created on first entry and updated on every subsequent edit.
    Normal users cannot modify or delete audit records.
    """
    result = models.ForeignKey(
        Result,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        help_text="The result this audit entry belongs to"
    )
    subject_mark = models.ForeignKey(
        SubjectMark,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        help_text="The subject mark that was changed"
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who made the change"
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ('CREATE', 'Created'),
            ('UPDATE', 'Updated'),
        ],
        help_text="Type of action performed"
    )
    old_obtained_marks = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text="Previous obtained marks (null on create)"
    )
    new_obtained_marks = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text="New obtained marks"
    )
    old_full_marks = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text="Previous full marks (null on create)"
    )
    new_full_marks = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text="New full marks"
    )
    old_gpa = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
        help_text="Previous GPA"
    )
    new_gpa = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
        help_text="New GPA"
    )
    old_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Previous percentage"
    )
    new_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="New percentage"
    )
    old_result_status = models.CharField(
        max_length=10, null=True, blank=True,
        help_text="Previous result status"
    )
    new_result_status = models.CharField(
        max_length=10, null=True, blank=True,
        help_text="New result status"
    )
    subject_name = models.CharField(
        max_length=200, blank=True,
        help_text="Subject name at time of change"
    )
    student_name = models.CharField(
        max_length=200, blank=True,
        help_text="Student name at time of change"
    )
    symbol_number = models.CharField(
        max_length=50, blank=True,
        help_text="Symbol number at time of change"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about the change"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Marks Audit Log"
        verbose_name_plural = "Marks Audit Logs"
        indexes = [
            models.Index(fields=['result', '-created_at']),
            models.Index(fields=['changed_by']),
        ]

    def __str__(self):
        return (
            f"{self.action} by {self.changed_by} "
            f"on {self.student_name} ({self.symbol_number}) "
            f"- {self.subject_name} at {self.created_at}"
        )