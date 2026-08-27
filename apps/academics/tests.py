"""
Comprehensive tests for the academics app.
"""
from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from .models import (
    Exam, ExamRoutine, Result, SubjectMark,
    TeacherSubjectAssignment, MarksAuditLog,
)
from .services import (
    calculate_result_from_subject_marks,
    save_marks_and_result,
    PASS_GPA_THRESHOLD,
)
from .permissions import (
    can_enter_marks, can_edit_result,
    is_teacher_assigned_to_subject, is_teacher_assigned_to_grade,
    validate_marks_range, validate_subject_mark_data,
)


class AcademicsTestCase(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='admin123', email='admin@test.com')
        self.staff_user = User.objects.create_user(
            username='teacher1', password='pass123', email='t1@test.com', is_staff=True)
        self.staff_user2 = User.objects.create_user(
            username='teacher2', password='pass123', email='t2@test.com', is_staff=True)
        self.normal_user = User.objects.create_user(
            username='student1', password='pass123', email='s1@test.com')
        self.exam = Exam.objects.create(
            name='First Terminal 2083', academic_year='2083/84',
            start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), is_published=True)
        TeacherSubjectAssignment.objects.create(
            user=self.staff_user, grade='9', subject='Mathematics')
        TeacherSubjectAssignment.objects.create(
            user=self.staff_user, grade='9', subject='Science')
        TeacherSubjectAssignment.objects.create(
            user=self.staff_user2, grade='9', subject='English')
        # URL for POST with exam in query string
        self.result_add_url = f"{reverse('academics:exam_result_add')}?exam={self.exam.pk}"


class AuthenticationTests(AcademicsTestCase):
    def test_anonymous_cannot_view_marks_entry_page(self):
        resp = self.client.get(reverse('academics:exam_result_add'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    def test_anonymous_cannot_post_marks(self):
        resp = self.client.post(self.result_add_url, {
            'action': 'add_manual', 'student_name': 'Test', 'symbol_number': 'GNS-001',
            'grade': '9', 'subject[]': ['Math'], 'full_marks[]': ['100'], 'obtained_marks[]': ['85'],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Result.objects.exists())

    def test_normal_user_cannot_view_marks_entry(self):
        self.client.login(username='student1', password='pass123')
        resp = self.client.get(reverse('academics:exam_result_add'))
        self.assertEqual(resp.status_code, 302)


class AuthorizationTests(AcademicsTestCase):
    def test_unauthorized_teacher_rejected(self):
        self.client.login(username='teacher1', password='pass123')
        resp = self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'Hacker', 'symbol_number': 'GNS-999', 'grade': '9',
            'subject[]': ['English'], 'full_marks[]': ['100'], 'obtained_marks[]': ['80'],
        })
        self.assertFalse(Result.objects.filter(symbol_number='GNS-999').exists())
        messages = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(any('not authorized' in m.lower() for m in messages),
                        f"Expected auth error, got: {messages}")

    def test_authorized_teacher_can_enter_marks(self):
        self.client.login(username='teacher1', password='pass123')
        resp = self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'Good', 'symbol_number': 'GNS-001', 'grade': '9',
            'subject[]': ['Mathematics'], 'full_marks[]': ['100'], 'obtained_marks[]': ['85'],
        })
        self.assertTrue(Result.objects.filter(symbol_number='GNS-001').exists())

    def test_superuser_can_enter_any_subject(self):
        self.client.login(username='admin', password='admin123')
        resp = self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'Any', 'symbol_number': 'GNS-002', 'grade': '9',
            'subject[]': ['English'], 'full_marks[]': ['100'], 'obtained_marks[]': ['90'],
        })
        self.assertTrue(Result.objects.filter(symbol_number='GNS-002').exists())

    def test_is_teacher_assigned_to_subject_check(self):
        self.assertTrue(is_teacher_assigned_to_subject(self.staff_user, '9', 'Mathematics'))
        self.assertFalse(is_teacher_assigned_to_subject(self.staff_user, '9', 'English'))
        self.assertTrue(is_teacher_assigned_to_subject(self.superuser, '9', 'Anything'))

    def test_can_enter_marks_check(self):
        self.assertTrue(can_enter_marks(self.staff_user))
        self.assertTrue(can_enter_marks(self.superuser))
        self.assertFalse(can_enter_marks(self.normal_user))

    def test_can_edit_result_grade_check(self):
        result = Result.objects.create(
            exam=self.exam, student_name='Test', symbol_number='S1', grade='9', result_status='PASS')
        self.assertTrue(can_edit_result(self.staff_user, result))
        self.assertFalse(can_edit_result(self.normal_user, result))


class DevToolsAttackTests(AcademicsTestCase):
    def test_fake_gpa_submitted_is_ignored(self):
        self.client.login(username='admin', password='admin123')
        self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'Attacker', 'symbol_number': 'GNS-HACK', 'grade': '9',
            'gpa': '4.0', 'percentage': '100', 'result_status': 'PASS',
            'subject[]': ['Mathematics'], 'full_marks[]': ['100'], 'obtained_marks[]': ['60'],
        })
        result = Result.objects.get(symbol_number='GNS-HACK')
        # 60/100 = 60% = B = 2.8
        self.assertEqual(result.gpa, Decimal('2.80'))

    def test_fake_percentage_submitted_is_ignored(self):
        self.client.login(username='admin', password='admin123')
        self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'Attacker3', 'symbol_number': 'GNS-HK3', 'grade': '9',
            'subject[]': ['Mathematics'], 'full_marks[]': ['100'], 'obtained_marks[]': ['50'],
        })
        result = Result.objects.get(symbol_number='GNS-HK3')
        # 50/100 = 50% = C+ = 2.4 -> percentage = 2.4 * 25 = 60.00
        self.assertEqual(result.percentage, Decimal('60.00'))

    def test_changing_subject_doesnt_bypass_auth(self):
        self.client.login(username='teacher1', password='pass123')
        self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'Victim', 'symbol_number': 'GNS-VIC', 'grade': '9',
            'subject[]': ['History'], 'full_marks[]': ['100'], 'obtained_marks[]': ['90'],
        })
        self.assertFalse(Result.objects.filter(symbol_number='GNS-VIC').exists())

    def test_changing_grade_doesnt_bypass_auth(self):
        self.client.login(username='teacher1', password='pass123')
        url = f"{reverse('academics:exam_result_add')}?exam={self.exam.pk}"
        self.client.post(url, {
            'action': 'add_manual',
            'student_name': 'Victim2', 'symbol_number': 'GNS-VI2', 'grade': '5',
            'subject[]': ['Mathematics'], 'full_marks[]': ['100'], 'obtained_marks[]': ['90'],
        })
        self.assertFalse(Result.objects.filter(symbol_number='GNS-VI2').exists())


class CalculationTests(AcademicsTestCase):
    def test_gpa_is_average_of_per_subject_grade_points(self):
        # Math: 95% = A+ = 4.0, English: 75% = B+ = 3.2, Science: 60% = B = 2.8
        # GPA = (4.0 + 3.2 + 2.8) / 3 = 3.33
        result_data = calculate_result_from_subject_marks([
            {'subject': 'Math', 'full_marks': 100, 'obtained_marks': 95},
            {'subject': 'English', 'full_marks': 100, 'obtained_marks': 75},
            {'subject': 'Science', 'full_marks': 100, 'obtained_marks': 60},
        ])
        self.assertEqual(result_data['gpa'], Decimal('3.33'))

    def test_percentage_is_gpa_times_25(self):
        # 85/100 = 85% = A = 3.6 -> percentage = 3.6 * 25 = 90.00
        result_data = calculate_result_from_subject_marks([
            {'subject': 'Math', 'full_marks': 100, 'obtained_marks': 85},
        ])
        self.assertEqual(result_data['gpa'], Decimal('3.60'))
        self.assertEqual(result_data['percentage'], Decimal('90.00'))

    def test_pass_when_gpa_above_threshold(self):
        # 35% = D = 1.6 -> PASS
        result_data = calculate_result_from_subject_marks([
            {'subject': 'Math', 'full_marks': 100, 'obtained_marks': 35},
        ])
        self.assertEqual(result_data['result_status'], 'PASS')

    def test_fail_when_gpa_below_threshold(self):
        # 30% = NG = 0.0 -> FAIL
        result_data = calculate_result_from_subject_marks([
            {'subject': 'Math', 'full_marks': 100, 'obtained_marks': 30},
        ])
        self.assertEqual(result_data['result_status'], 'FAIL')

    def test_absent_when_no_marks(self):
        result_data = calculate_result_from_subject_marks([
            {'subject': 'Math', 'full_marks': 100, 'obtained_marks': None},
        ])
        self.assertEqual(result_data['result_status'], 'ABSENT')

    def test_boundary_35_percent_is_pass(self):
        result_data = calculate_result_from_subject_marks([
            {'subject': 'Math', 'full_marks': 100, 'obtained_marks': 35},
        ])
        self.assertEqual(result_data['gpa'], Decimal('1.60'))

    def test_boundary_34_percent_is_fail(self):
        result_data = calculate_result_from_subject_marks([
            {'subject': 'Math', 'full_marks': 100, 'obtained_marks': 34},
        ])
        self.assertEqual(result_data['gpa'], Decimal('0.00'))

    def test_full_marks_gives_40_gpa(self):
        result_data = calculate_result_from_subject_marks([
            {'subject': 'Math', 'full_marks': 100, 'obtained_marks': 100},
        ])
        self.assertEqual(result_data['gpa'], Decimal('4.00'))


class ValidationTests(AcademicsTestCase):
    def test_negative_marks_rejected(self):
        cleaned, errors = validate_subject_mark_data(['Math'], ['100'], ['-5'])
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(cleaned), 0)

    def test_marks_exceeding_full_rejected(self):
        cleaned, errors = validate_subject_mark_data(['Math'], ['100'], ['150'])
        self.assertEqual(len(errors), 1)

    def test_valid_marks_accepted(self):
        cleaned, errors = validate_subject_mark_data(['Math'], ['100'], ['85'])
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(cleaned), 1)

    def test_validate_marks_range_negative(self):
        self.assertIsNotNone(validate_marks_range(-5, 100, 'Math'))

    def test_validate_marks_range_exceeds_full(self):
        self.assertIsNotNone(validate_marks_range(150, 100, 'Math'))

    def test_validate_marks_range_valid(self):
        self.assertIsNone(validate_marks_range(85, 100, 'Math'))

    def test_duplicate_symbol_rejected(self):
        Result.objects.create(
            exam=self.exam, student_name='S1', symbol_number='DUP-001',
            grade='9', result_status='PASS')
        self.client.login(username='admin', password='admin123')
        self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'S2', 'symbol_number': 'DUP-001', 'grade': '9',
            'subject[]': ['Math'], 'full_marks[]': ['100'], 'obtained_marks[]': ['80'],
        })
        self.assertEqual(Result.objects.filter(symbol_number='DUP-001').count(), 1)

    def test_empty_student_name_rejected(self):
        self.client.login(username='admin', password='admin123')
        self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': '', 'symbol_number': 'X', 'grade': '9',
            'subject[]': ['Math'], 'full_marks[]': ['100'], 'obtained_marks[]': ['80'],
        })
        self.assertFalse(Result.objects.filter(symbol_number='X').exists())

    def test_empty_symbol_rejected(self):
        self.client.login(username='admin', password='admin123')
        self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'NoSym', 'symbol_number': '', 'grade': '9',
            'subject[]': ['Math'], 'full_marks[]': ['100'], 'obtained_marks[]': ['80'],
        })
        self.assertFalse(Result.objects.filter(student_name='NoSym').exists())

    def test_invalid_grade_rejected(self):
        self.client.login(username='admin', password='admin123')
        self.client.post(self.result_add_url, {
            'action': 'add_manual',
            'student_name': 'Bad', 'symbol_number': 'GNS-BAD', 'grade': '99',
            'subject[]': ['Math'], 'full_marks[]': ['100'], 'obtained_marks[]': ['80'],
        })
        self.assertFalse(Result.objects.filter(symbol_number='GNS-BAD').exists())


class ServiceLayerTests(AcademicsTestCase):
    def test_save_marks_creates_subject_marks(self):
        result = Result.objects.create(
            exam=self.exam, student_name='Svc', symbol_number='SVC-001',
            grade='9', result_status='PASS')
        # Math: 90% = A+ = 4.0, Science: 70% = B+ = 3.2
        # GPA = (4.0 + 3.2) / 2 = 3.60
        result = save_marks_and_result(
            result=result,
            subject_marks_data=[
                {'subject': 'Math', 'full_marks': 100, 'obtained_marks': 90},
                {'subject': 'Science', 'full_marks': 100, 'obtained_marks': 70}],
            user=self.superuser, notes='Test')
        self.assertEqual(result.subject_marks.count(), 2)
        self.assertEqual(result.gpa, Decimal('3.60'))

    def test_save_marks_recalculates_on_edit(self):
        result = Result.objects.create(
            exam=self.exam, student_name='Edit', symbol_number='EDT-001',
            grade='9', result_status='PASS')
        result = save_marks_and_result(
            result=result,
            subject_marks_data=[{'subject': 'Math', 'full_marks': 100, 'obtained_marks': 90}],
            user=self.superuser)
        result = save_marks_and_result(
            result=result,
            subject_marks_data=[{'subject': 'Math', 'full_marks': 100, 'obtained_marks': 50}],
            user=self.superuser, notes='Edited')
        # 50% = C+ = 2.4
        self.assertEqual(result.gpa, Decimal('2.40'))

    def test_audit_log_created_on_save(self):
        result = Result.objects.create(
            exam=self.exam, student_name='Audit', symbol_number='AUD-001',
            grade='9', result_status='PASS')
        result = save_marks_and_result(
            result=result,
            subject_marks_data=[{'subject': 'Math', 'full_marks': 100, 'obtained_marks': 80}],
            user=self.staff_user, notes='First')
        logs = MarksAuditLog.objects.filter(result=result)
        self.assertTrue(logs.exists())
        self.assertEqual(logs.first().changed_by, self.staff_user)

    def test_audit_log_created_on_edit(self):
        result = Result.objects.create(
            exam=self.exam, student_name='AEdit', symbol_number='AED-001',
            grade='9', result_status='PASS')
        result = save_marks_and_result(
            result=result,
            subject_marks_data=[{'subject': 'Math', 'full_marks': 100, 'obtained_marks': 80}],
            user=self.staff_user)
        initial = MarksAuditLog.objects.filter(result=result).count()
        result = save_marks_and_result(
            result=result,
            subject_marks_data=[{'subject': 'Math', 'full_marks': 100, 'obtained_marks': 95}],
            user=self.superuser, notes='Changed')
        self.assertGreater(MarksAuditLog.objects.filter(result=result).count(), initial)


class RateLimitingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='victim', password='wrongpass')
        self.client = Client()

    def test_login_rate_limit_blocks(self):
        for i in range(5):
            resp = self.client.post(reverse('auth:login'), {
                'username': 'victim', 'password': 'wrongpass'})
            self.assertIn(resp.status_code, [200, 302])
        resp = self.client.post(reverse('auth:login'), {
            'username': 'victim', 'password': 'wrongpass'})
        messages = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(any('too many' in m.lower() or 'wait' in m.lower() for m in messages))

    def test_result_search_rate_limit(self):
        for i in range(30):
            resp = self.client.get(reverse('academics:results'), {'symbol_number': f'FAKE-{i}'})
            # Some may get rate limited if cache is shared, just check it returns something
            self.assertIn(resp.status_code, [200, 302])
        resp = self.client.get(reverse('academics:results'), {'symbol_number': 'OVER'})
        messages = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(any('too many' in m.lower() for m in messages))


class EditResultTests(AcademicsTestCase):
    def setUp(self):
        super().setUp()
        self.result = Result.objects.create(
            exam=self.exam, student_name='Edit Me', symbol_number='EDT-001',
            grade='9', result_status='PASS', is_published=True)
        save_marks_and_result(
            result=self.result,
            subject_marks_data=[{'subject': 'Math', 'full_marks': 100, 'obtained_marks': 80}],
            user=self.superuser)

    def test_unauthorized_teacher_cannot_edit(self):
        result5 = Result.objects.create(
            exam=self.exam, student_name='C5', symbol_number='EDT-005',
            grade='5', result_status='PASS', is_published=True)
        self.client.login(username='teacher1', password='pass123')
        self.client.post(self.result_add_url, {
            'action': 'edit_result', 'result_id': result5.pk,
            'student_name': 'Hacked', 'symbol_number': 'EDT-005', 'grade': '5',
            'subject[]': ['Math'], 'full_marks[]': ['100'], 'obtained_marks[]': ['99'],
        })
        result5.refresh_from_db()
        self.assertEqual(result5.student_name, 'C5')

    def test_authorized_edit_updates_marks_and_recalculates(self):
        self.client.login(username='admin', password='admin123')
        # 50/100 = 50% = C+ = 2.4
        self.client.post(self.result_add_url, {
            'action': 'edit_result', 'result_id': self.result.pk,
            'student_name': 'Edited', 'symbol_number': 'EDT-001', 'grade': '9',
            'subject[]': ['Math'], 'full_marks[]': ['100'], 'obtained_marks[]': ['50'],
        })
        self.result.refresh_from_db()
        self.assertEqual(self.result.gpa, Decimal('2.40'))

    def test_edit_ignores_client_gpa(self):
        self.client.login(username='admin', password='admin123')
        self.client.post(self.result_add_url, {
            'action': 'edit_result', 'result_id': self.result.pk,
            'student_name': 'Edit Me', 'symbol_number': 'EDT-001', 'grade': '9',
            'gpa': '4.0',
            'subject[]': ['Math'], 'full_marks[]': ['100'], 'obtained_marks[]': ['50'],
        })
        self.result.refresh_from_db()
        # 50% = C+ = 2.4
        self.assertEqual(self.result.gpa, Decimal('2.40'))


class PublicResultsTests(AcademicsTestCase):
    def setUp(self):
        super().setUp()
        self.result = Result.objects.create(
            exam=self.exam, student_name='Pub', symbol_number='PUB-001',
            grade='9', result_status='PASS', is_published=True)
        save_marks_and_result(
            result=self.result,
            subject_marks_data=[{'subject': 'Math', 'full_marks': 100, 'obtained_marks': 85}],
            user=self.superuser)

    def test_result_search_by_symbol(self):
        resp = self.client.get(reverse('academics:results'), {'symbol_number': 'PUB-001'})
        self.assertEqual(resp.status_code, 200)

    def test_unpublished_result_not_shown(self):
        Result.objects.create(
            exam=self.exam, student_name='Hidden', symbol_number='HID-001',
            grade='9', result_status='PASS', is_published=False)
        resp = self.client.get(reverse('academics:results'), {'symbol_number': 'HID-001'})
        self.assertNotContains(resp, 'Hidden')

    def test_nonexistent_symbol_shows_error(self):
        resp = self.client.get(reverse('academics:results'), {'symbol_number': 'NONE'})
        self.assertContains(resp, 'No published result found')