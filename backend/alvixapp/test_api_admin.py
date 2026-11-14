"""Tests for /api/v1/admin/ (admin core pages) and the legacy views sharing their logic."""

import unittest

from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from . import views
from .models import (
    AdminCourse,
    AssignmentSubmission,
    AvatarSettings,
    GeneratedCourse,
    Notification,
    DailyLesson,
    Profile,
    QuizSubmission,
    Report,
)

API = '/api/v1/admin'
LEGACY = settings.ALVIX_FRONTEND == 'templates'


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])  # fast tests
class AdminApiBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('boss', 'boss@x.com', 'pw', is_staff=True)
        self.student = User.objects.create_user('stud', 'stud@x.com', 'pw', first_name='Ali', last_name='Khan')
        self.course = AdminCourse.objects.create(title='Python Mastery')
        GeneratedCourse.objects.create(user=self.student, admin_course=self.course, level='Beginner', pace='Normal')
        self.report = Report.objects.create(
            student=self.student, course_name='Python Mastery', problem_type='technical',
            problem_title='Video broken', problem_description='x' * 60,
        )
        self.client.force_login(self.admin)


class PermissionTests(AdminApiBase):
    ENDPOINTS = ['dashboard/', 'users/', 'reports/', 'notifications/', 'analytics/', 'avatar-settings/']

    def test_anonymous_rejected(self):
        self.client.logout()
        for ep in self.ENDPOINTS:
            self.assertIn(self.client.get(f'{API}/{ep}').status_code, (401, 403), ep)

    def test_student_rejected(self):
        self.client.force_login(self.student)
        for ep in self.ENDPOINTS:
            self.assertEqual(self.client.get(f'{API}/{ep}').status_code, 403, ep)
        res = self.client.post(f'{API}/users/', {'action': 'delete', 'user_id': self.admin.id})
        self.assertEqual(res.status_code, 403)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())
        self.assertEqual(self.client.post(f'{API}/reports/{self.report.id}/delete/').status_code, 403)
        self.assertTrue(Report.objects.filter(id=self.report.id).exists())


class DashboardTests(AdminApiBase):
    def test_counts(self):
        data = self.client.get(f'{API}/dashboard/').json()
        self.assertEqual(data, {'total_courses': 1, 'total_students': 1, 'pending_reports_count': 1, 'total_enrollments': 1})


class UserManagementTests(AdminApiBase):
    def test_list(self):
        Profile.objects.filter(user=self.student).update(phone='0300', dob='2001-02-03')
        users = {u['username']: u for u in self.client.get(f'{API}/users/').json()['users']}
        row = users['stud']
        self.assertEqual(row['email'], 'stud@x.com')
        self.assertEqual(row['profile'], {'phone': '0300', 'dob': '2001-02-03'})
        self.assertEqual(row['custom_generated_courses'], ['Python Mastery'])
        self.assertTrue(row['is_active'])

    def test_edit(self):
        res = self.client.post(f'{API}/users/', {
            'action': 'edit', 'user_id': self.student.id, 'username': 'stud2', 'email': 'n@x.com',
            'phone': '0311', 'dob': '2000-01-01', 'password': 'newpass123',
        })
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['redirect'], '/user_management/')
        self.assertEqual(body['messages'][0]['message'], 'User stud2 updated successfully!')
        self.student.refresh_from_db()
        self.assertEqual(self.student.username, 'stud2')
        self.assertTrue(self.student.check_password('newpass123'))
        self.assertEqual(self.student.profile.phone, '0311')

    def test_delete_and_errors(self):
        res = self.client.post(f'{API}/users/', {'action': 'delete', 'user_id': self.student.id})
        self.assertEqual(res.json()['messages'][0]['message'], 'User stud deleted successfully.')
        self.assertFalse(User.objects.filter(username='stud').exists())
        self.assertEqual(self.client.post(f'{API}/users/', {'action': 'delete', 'user_id': 9999}).status_code, 404)
        self.assertEqual(self.client.post(f'{API}/users/', {'action': 'nope'}).status_code, 400)


class ReportTests(AdminApiBase):
    def test_list(self):
        data = self.client.get(f'{API}/reports/').json()
        self.assertEqual(data['total_submissions'], 1)
        self.assertEqual(data['pending_reports'], 1)
        self.assertEqual(data['reviewed_reports'], 0)
        # same (UTC-date) computation as the view
        self.assertEqual(data['active_today'], Report.objects.filter(created_at__date=timezone.now().date()).count())
        r = data['reports'][0]
        self.assertEqual(r['student_name'], 'Ali Khan')
        self.assertEqual(r['problem_type_display'], 'Technical Issue')
        self.assertEqual(r['status'], 'pending')

    def test_respond(self):
        res = self.client.post(f'{API}/reports/{self.report.id}/respond/', {'feedback': 'Fixed now'}).json()
        self.assertEqual(res['messages'][0]['message'], f'Response delivered to student for Report #{self.report.id}!')
        self.assertEqual(res['redirect'], '/admin_reports/')
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'resolved')
        n = Notification.objects.get(recipient_user=self.student)
        self.assertIn('Admin Response: Fixed now', n.notification_body)

    def test_respond_empty_does_nothing(self):
        res = self.client.post(f'{API}/reports/{self.report.id}/respond/', {'feedback': '  '}).json()
        self.assertNotIn('messages', res)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'pending')

    def test_delete(self):
        res = self.client.post(f'{API}/reports/{self.report.id}/delete/').json()
        self.assertEqual(res['messages'][0]['message'], f'Report #{self.report.id} deleted successfully.')
        self.assertFalse(Report.objects.exists())
        self.assertEqual(self.client.post(f'{API}/reports/{self.report.id}/delete/').status_code, 404)


class NotificationTests(AdminApiBase):
    def test_get_and_specific_student(self):
        data = self.client.get(f'{API}/notifications/').json()
        self.assertEqual(data['students_list'], [{'id': self.student.id, 'username': 'stud', 'get_full_name': 'Ali Khan'}])
        self.assertEqual(data['dispatch_history'], [])
        res = self.client.post(f'{API}/notifications/', {
            'target_recipient': 'specific_student', 'specific_student_id': self.student.id,
            'category_type': 'alert', 'subject_heading': 'Hi', 'notification_body': 'Body',
        }).json()
        self.assertEqual(res['messages'][0]['message'], 'Notification sent to stud!')
        self.assertEqual(res['redirect'], '/admin_notifications/')
        h = self.client.get(f'{API}/notifications/').json()['dispatch_history'][0]
        self.assertEqual(h['subject_heading'], 'Hi')
        self.assertEqual(h['get_target_recipient_display'], 'Specific Student')
        self.assertEqual(h['get_category_type_display'], 'Urgent Alert')
        self.assertTrue(h['created_at'])

    def test_broadcast_and_empty(self):
        res = self.client.post(f'{API}/notifications/', {
            'target_recipient': 'enrolled_students', 'category_type': 'course_update',
            'subject_heading': 'S', 'notification_body': 'B',
        }).json()
        self.assertEqual(res['messages'][0]['message'], 'Broadcast notification dispatched to students!')
        h = self.client.get(f'{API}/notifications/').json()['dispatch_history'][0]
        self.assertEqual(h['get_category_type_display'], 'course_update')
        self.assertEqual(self.client.post(f'{API}/notifications/', {'target_recipient': 'all_students'}).status_code, 400)


class AnalyticsTests(AdminApiBase):
    def test_keys(self):
        AssignmentSubmission.objects.create(user=self.student)
        data = self.client.get(f'{API}/analytics/').json()
        for key in ('total_courses', 'total_students', 'total_enrollments', 'total_assignments', 'total_quizzes',
                    'completion_rate', 'student_satisfaction', 'top_performing_courses', 'assignment_submissions',
                    'quiz_performance', 'recent_activities'):
            self.assertIn(key, data)
        self.assertEqual(data['completion_rate'], 82.5)
        self.assertEqual(data['quiz_performance'], 84)   # plain numbers: the bar width is "84%"
        self.assertEqual(data['student_satisfaction'], 96)
        top = data['top_performing_courses'][0]
        self.assertEqual(top['title'], 'Python Mastery')
        self.assertEqual(top['student_count'], 1)
        self.assertEqual(top['rating'], 0.0)   # no quizzes yet
        act = data['recent_activities'][0]
        self.assertEqual(act['user'], {'username': 'stud'})
        self.assertEqual(act['action_description'], 'submitted assignment for Lesson')
        self.assertTrue(act['timestamp'])

    def test_rating_and_ranking(self):
        other = AdminCourse.objects.create(title='Rust Systems')
        gen = GeneratedCourse.objects.create(user=self.student, admin_course=other, level='Beginner', pace='Normal')
        lesson = DailyLesson.objects.create(generated_course=gen, day_number=1, title='Ownership', content='c')
        QuizSubmission.objects.create(user=self.student, lesson=lesson, score=4, total_questions=5, percentage=80)
        QuizSubmission.objects.create(user=self.student, lesson=lesson, score=5, total_questions=5, percentage=100)
        AssignmentSubmission.objects.create(user=self.student, lesson=lesson)
        data = self.client.get(f'{API}/analytics/').json()
        top = data['top_performing_courses']
        self.assertEqual([t['title'] for t in top], ['Rust Systems', 'Python Mastery'])
        self.assertEqual(top[0]['rating'], 4.5)   # avg 90% -> 90 / 20
        self.assertEqual(data['recent_activities'][0]['action_description'], 'submitted assignment for Ownership')

    def test_template_renders_values(self):
        """Render the legacy view directly (its URL serves the SPA in react mode)."""
        AssignmentSubmission.objects.create(user=self.student)
        request = RequestFactory().get('/analytics/')
        request.user = self.admin
        html = views.analytics(request).content.decode()
        self.assertIn('style="width: 84%"', html)
        self.assertIn('style="width: 96%"', html)
        self.assertIn('stud submitted assignment for Lesson', html)
        self.assertIn('\u2b50 0.0', html)
        self.assertIn('<td>1</td>', html)


class AvatarSettingsTests(AdminApiBase):
    def test_get_widgets(self):
        data = self.client.get(f'{API}/avatar-settings/').json()
        w = data['form']['avatar_name']
        self.assertEqual(w['type'], 'text')
        self.assertEqual(w['value'], 'Inara')
        self.assertEqual(w['attrs']['class'], 'form-control')
        self.assertEqual(w['attrs']['placeholder'], 'e.g. Inara')
        self.assertEqual(w['attrs']['maxlength'], '100')
        self.assertTrue(w['attrs']['required'])
        self.assertEqual(w['attrs']['id'], 'id_avatar_name')
        self.assertNotIn('required', data['form']['university_or_department']['attrs'])
        cb = data['form']['play_full_intro_every_day']
        self.assertEqual(cb['type'], 'checkbox')
        self.assertEqual(cb['attrs']['class'], 'form-check-input')
        self.assertNotIn('checked', cb['attrs'])
        self.assertEqual(data['avatar_settings']['get_spoken_name'], 'ee-nah-rah')
        self.assertEqual(set(data['asset_status']['file_status']), {'idle', 'wave', 'blink', 'mouth_open'})

    def test_post_valid_and_invalid(self):
        res = self.client.post(f'{API}/avatar-settings/', {
            'avatar_name': 'Zara', 'developer_name': 'Dev', 'university_or_department': '',
            'avatar_name_pronunciation': '', 'play_full_intro_every_day': 'on',
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['messages'][0]['message'], "Avatar settings for 'Zara' updated successfully!")
        s = AvatarSettings.get_settings()
        self.assertEqual(s.avatar_name, 'Zara')
        self.assertTrue(s.play_full_intro_every_day)
        self.assertIn('checked', self.client.get(f'{API}/avatar-settings/').json()['form']['play_full_intro_every_day']['attrs'])

        res = self.client.post(f'{API}/avatar-settings/', {'avatar_name': '', 'developer_name': 'Dev'})
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertIn('avatar_name', body['errors'])
        self.assertEqual(body['messages'][0], {'tags': 'error', 'message': 'Please correct the errors in the form below.'})
        self.assertEqual(body['form']['avatar_name']['attrs']['aria-invalid'], 'true')
        self.assertEqual(body['form']['developer_name']['value'], 'Dev')


@unittest.skipUnless(LEGACY, 'legacy template views are only routed when ALVIX_FRONTEND=templates')
class LegacyViewTests(AdminApiBase):
    def test_pages_render(self):
        for url in ('/admindashboard/', '/user_management/', '/admin_reports/', '/admin_notifications/',
                    '/analytics/', '/admindashboard/avatar-settings/'):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_legacy_actions(self):
        res = self.client.post('/admin-reports/respond/%d/' % self.report.id, {'feedback': 'ok'})
        self.assertRedirects(res, '/admin_reports/', fetch_redirect_response=False)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'resolved')
        res = self.client.post('/user_management/', {'action': 'edit', 'user_id': self.student.id, 'username': 'zz'})
        self.assertRedirects(res, '/user_management/', fetch_redirect_response=False)
        res = self.client.get('/delete_user/%d/' % self.student.id)
        self.assertRedirects(res, '/user_management/', fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(id=self.student.id).exists())
