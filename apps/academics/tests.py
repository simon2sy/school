from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from .forms import ExamRoutineForm
from .models import Exam, ExamRoutine


class ExamRoutineModelTests(TestCase):
    def setUp(self):
        self.exam = Exam.objects.create(
            name="First Term",
            academic_year="2083/84",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            is_published=True,
        )

    def test_grade_choices_cover_classes_1_to_10(self):
        values = [v for v, _ in ExamRoutine.GRADE_CHOICES]
        self.assertEqual(values, [str(i) for i in range(1, 11)])

    def test_routine_ordering_by_grade_date_time(self):
        ExamRoutine.objects.create(
            exam=self.exam, grade="10", subject="Science",
            exam_date=date(2026, 1, 2), start_time=time(9, 0),
            end_time=time(11, 0),
        )
        ExamRoutine.objects.create(
            exam=self.exam, grade="1", subject="English",
            exam_date=date(2026, 1, 5), start_time=time(10, 0),
            end_time=time(12, 0),
        )
        grades = list(
            ExamRoutine.objects.filter(exam=self.exam).values_list(
                'grade', flat=True
            )
        )
        self.assertEqual(grades, ['1', '10'])

class ExamRoutineFormTests(TestCase):
    def setUp(self):
        self.exam = Exam.objects.create(
            name="First Term",
            academic_year="2083/84",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

    def test_end_time_must_be_after_start_time(self):
        form = ExamRoutineForm(data={
            'exam': self.exam.pk, 'grade': '1', 'subject': 'Math',
            'exam_date': date(2026, 1, 5),
            'start_time': time(12, 0), 'end_time': time(10, 0),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)
        self.assertIn('later', form.errors['end_time'][0])

    def test_exam_date_must_be_within_exam_period(self):
        form = ExamRoutineForm(data={
            'exam': self.exam.pk, 'grade': '2', 'subject': 'Nepali',
            'exam_date': date(2026, 3, 5),
            'start_time': time(9, 0), 'end_time': time(10, 0),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('exam_date', form.errors)
        self.assertIn('exam period', form.errors['exam_date'][0])

    def test_valid_form_passes(self):
        form = ExamRoutineForm(data={
            'exam': self.exam.pk, 'grade': '10', 'subject': 'Science',
            'exam_date': date(2026, 1, 10),
            'start_time': time(9, 0), 'end_time': time(11, 0),
            'room': 'Hall C',
        })
        self.assertTrue(form.is_valid())

class ExamRoutineViewTests(TestCase):
    def setUp(self):
        self.published = Exam.objects.create(
            name="First Term", academic_year="2083/84",
            start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
            is_published=True,
        )
        self.unpublished = Exam.objects.create(
            name="Secret Exam", academic_year="2082/83",
            start_date=date(2026, 2, 1), end_date=date(2026, 2, 28),
            is_published=False,
        )
        ExamRoutine.objects.create(
            exam=self.published, grade="1", subject="English",
            exam_date=date(2026, 1, 5), start_time=time(10, 0),
            end_time=time(12, 0), room="Hall A",
        )
        ExamRoutine.objects.create(
            exam=self.published, grade="1", subject="Math",
            exam_date=date(2026, 1, 7), start_time=time(8, 0),
            end_time=time(10, 0), room="Hall B",
        )
        ExamRoutine.objects.create(
            exam=self.published, grade="10", subject="Science",
            exam_date=date(2026, 1, 9), start_time=time(9, 0),
            end_time=time(11, 0), room="Hall C",
        )

    def test_unpublished_exam_never_visible(self):
        response = self.client.get(reverse('academics:exam_routine'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Secret Exam")
        response = self.client.get(
            reverse('academics:exam_routine_detail', args=[self.unpublished.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First Term")
        self.assertNotContains(response, "Secret Exam")

    def test_all_classes_and_filter_by_class(self):
        response = self.client.get(reverse('academics:exam_routine'))
        self.assertContains(response, "English")
        self.assertContains(response, "Math")
        self.assertContains(response, "Science")
        self.assertContains(response, "Class 10")

        response = self.client.get(
            reverse('academics:exam_routine'),
            {'exam': self.published.pk, 'grade': '1'},
        )
        self.assertContains(response, "English")
        self.assertContains(response, "Math")
        # Only Class 1 routines remain in the filtered queryset.
        subjects = [r.subject for r in response.context['routines']]
        self.assertEqual(subjects, ['English', 'Math'])

    def test_class_selection_remains_selected(self):
        response = self.client.get(
            reverse('academics:exam_routine'),
            {'exam': self.published.pk, 'grade': '10'},
        )
        self.assertContains(response, 'value="10" selected')

    def test_no_routines_message(self):
        response = self.client.get(
            reverse('academics:exam_routine'),
            {'exam': self.published.pk, 'grade': '4'},
        )
        self.assertContains(response, "No Routines Found")

    def test_day_displayed_from_date(self):
        response = self.client.get(
            reverse('academics:exam_routine'),
            {'exam': self.published.pk, 'grade': '1'},
        )
        self.assertContains(response, "Monday")  # 2026-01-05 is a Monday
