"""Tests for /api/v1/student/ (dashboard, assessment, profile, notifications, reports,
performance, settings) and the legacy template views that share page_context/student.py."""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import (
    AdminCourse,
    CourseLevel,
    DailyLesson,
    GeneratedCourse,
    Notification,
    Profile,
    Report,
    StudentAssessment,
    StudentNotificationStatus,
    UserSettings,
)

API = '/api/v1/student/'

# 1x1 transparent GIF
TINY_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00'
    b',\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


class StudentApiBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('stud', 'stud@example.com', 'Str0ng-pass!')
        self.profile = Profile.objects.get(user=self.user)
        self.client.force_login(self.user)

    def complete_assessment(self):
        Profile.objects.filter(user=self.user).update(assessment_completed=True)

    def make_course(self, user=None, lessons=2):
        admin_course = AdminCourse.objects.create(title='Python Basics', description='Learn python')
        level = CourseLevel.objects.create(parent_course=admin_course, level='Beginner', title='Python Basics - Beginner')
        gc = GeneratedCourse.objects.create(user=user or self.user, admin_course=admin_course, course_level=level,
                                            level='Beginner', pace='Standard')
        for n in range(1, lessons + 1):
            DailyLesson.objects.create(generated_course=gc, day_number=n, title=f'Lesson {n}', content='x')
        return gc


class AuthRequiredTests(TestCase):
    def test_all_endpoints_require_login(self):
        for name in ('dashboard', 'assessment', 'profile', 'notifications', 'reports', 'performance', 'settings'):
            res = self.client.get(f'{API}{name}/')
            self.assertIn(res.status_code, (401, 403), name)


class DashboardApiTests(StudentApiBase):
    def test_redirects_to_assessment_when_not_completed(self):
        self.assertEqual(self.client.get(f'{API}dashboard/').json(), {'redirect': '/assessment/'})

    def test_staff_skips_assessment(self):
        staff = User.objects.create_user('boss', 'boss@example.com', 'p', is_staff=True)
        self.client.force_login(staff)
        self.assertNotIn('redirect', self.client.get(f'{API}dashboard/').json())

    def test_empty_dashboard_keys(self):
        self.complete_assessment()
        data = self.client.get(f'{API}dashboard/').json()
        for key in ('user', 'generated_courses', 'overall_progress', 'grade', 'ai_remarks',
                    'popup_notification', 'suggested_course', 'certificate_unlocked', 'active_course'):
            self.assertIn(key, data)
        self.assertEqual(data['generated_courses'], [])
        self.assertEqual(data['grade'], 'Beginner')
        self.assertEqual(data['overall_progress'], 0)
        self.assertIsNone(data['popup_notification'])
        self.assertFalse(data['certificate_unlocked'])
        self.assertEqual(data['ai_remarks'], 'No active course found. Generate a course to begin tracking your analytics.')

    def test_dashboard_with_course(self):
        self.complete_assessment()
        gc = self.make_course()
        data = self.client.get(f'{API}dashboard/').json()
        self.assertEqual(len(data['generated_courses']), 1)
        course = data['generated_courses'][0]
        self.assertEqual(course['id'], gc.id)
        self.assertEqual(course['admin_course']['title'], 'Python Basics')
        self.assertEqual(course['daily_lessons_count'], 2)
        self.assertEqual(course['first_lesson_id'], gc.daily_lessons.first().id)
        self.assertEqual(course['tier_display'], 'Harvard / MIT / Stanford St…')
        self.assertEqual(data['grade'], 'Needs Improvement')
        self.assertEqual(data['active_course']['id'], gc.id)
        # Suggested course only when there are no generated courses and no assessment
        self.assertIsNone(data['suggested_course'])

    def test_suggested_course_from_assessment(self):
        self.complete_assessment()
        course = AdminCourse.objects.create(title='Design 101', description='')
        StudentAssessment.objects.create(user=self.user, interest=course)
        data = self.client.get(f'{API}dashboard/').json()
        self.assertEqual(data['suggested_course']['title'], 'Design 101')
        self.assertEqual(data['suggested_course']['description_display'],
                         'Curated from database based on your learning goals.')

    def test_only_own_courses(self):
        self.complete_assessment()
        other = User.objects.create_user('other', 'o@example.com', 'p')
        self.make_course(user=other)
        self.assertEqual(self.client.get(f'{API}dashboard/').json()['generated_courses'], [])

    def test_legacy_dashboard_view(self):
        self.assertRedirects(self.client.get('/dashboard/'), '/assessment/', fetch_redirect_response=False)


class AssessmentApiTests(StudentApiBase):
    valid = {
        'interest_area': 'Development',
        'goal': 'Practical',
        'expectations': 'I want to build real production web applications end to end.',
    }

    def test_get(self):
        data = self.client.get(f'{API}assessment/').json()
        self.assertFalse(data['is_retake'])
        self.assertEqual(data['form'], {'interest_area': None, 'goal': None, 'expectations': None})
        self.assertTrue(self.client.get(f'{API}assessment/?retake=true').json()['is_retake'])

    @patch('alvixapp.course_recommendation.suggest_best_fit_course_with_ai', return_value=(None, 'r', 'Beginner'))
    def test_post_valid(self, _mock):
        res = self.client.post(f'{API}assessment/', self.valid)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['redirect'], '/suggested_courses/')
        self.assertEqual(data['messages'][0]['message'],
                         'Assessment complete! Review your AI-suggested learning paths below.')
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.assessment_completed)
        self.assertEqual(self.profile.interest_area, 'Development')
        self.assertEqual(StudentAssessment.objects.filter(user=self.user).count(), 1)

        # Second time is a retake; GET pre-populates
        res = self.client.post(f'{API}assessment/', self.valid)
        self.assertEqual(res.json()['messages'][0]['message'],
                         'Assessment updated successfully! Review your AI-suggested learning paths below.')
        self.assertEqual(self.client.get(f'{API}assessment/').json()['form']['goal'], 'Practical')

    def test_post_invalid(self):
        res = self.client.post(f'{API}assessment/', {**self.valid, 'expectations': 'short'})
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertIn('expectations', data['errors'])
        self.assertEqual(data['form']['interest_area'], 'Development')
        self.assertEqual(data['messages'][0]['tags'], 'error')
        self.assertFalse(Profile.objects.get(user=self.user).assessment_completed)


class ProfileApiTests(StudentApiBase):
    def test_get(self):
        data = self.client.get(f'{API}profile/').json()
        self.assertEqual(data['user']['email'], 'stud@example.com')
        self.assertEqual(data['profile']['user']['username'], 'stud')
        self.assertIsNone(data['enrolled_course'])

    def test_post_multipart(self):
        self.profile.goal = 'Keep me'
        self.profile.save()
        pic = SimpleUploadedFile('me.gif', TINY_GIF, content_type='image/gif')
        res = self.client.post(f'{API}profile/', {
            'full_name': 'New Name', 'email': 'new@example.com', 'phone': '123', 'dob': '2000-01-02',
            'gender': 'Female', 'profile_picture': pic,
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['redirect'], '/profile/')
        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.profile.full_name, 'New Name')
        self.assertEqual(self.profile.gender, 'Female')
        self.assertEqual(str(self.profile.dob), '2000-01-02')
        self.assertEqual(self.profile.goal, 'Keep me')
        self.assertTrue(self.profile.profile_picture.name.startswith('profile_pictures/'))
        self.assertEqual(self.user.email, 'new@example.com')
        self.profile.profile_picture.delete(save=False)

    def test_legacy_profile_post(self):
        res = self.client.post('/profile/', {'full_name': 'X', 'email': 'x@example.com', 'phone': '', 'gender': ''})
        self.assertRedirects(res, '/profile/', fetch_redirect_response=False)


class NotificationsApiTests(StudentApiBase):
    def test_list_and_mark_read(self):
        n = Notification.objects.create(subject_heading='Hello', notification_body='Body', category_type='alert')
        other = User.objects.create_user('other', 'o@example.com', 'p')
        Notification.objects.create(subject_heading='Private', target_recipient='specific_student', recipient_user=other)

        data = self.client.get(f'{API}notifications/').json()
        self.assertEqual(len(data['notifications']), 1)
        item = data['notifications'][0]
        self.assertFalse(item['is_read'])
        self.assertEqual(item['notification']['id'], n.id)
        self.assertEqual(item['notification']['category_type_display'], 'Urgent Alert')

        res = self.client.post(f'/notifications/read/{n.id}/')
        self.assertEqual(res.json()['status'], 'success')
        item = self.client.get(f'{API}notifications/').json()['notifications'][0]
        self.assertTrue(item['is_read'])
        self.assertIsNotNone(item['read_at'])
        self.assertTrue(StudentNotificationStatus.objects.get(user=self.user, notification=n).is_read)


class ReportsApiTests(StudentApiBase):
    def test_get(self):
        Report.objects.create(student=self.user, course_name='C', problem_type='other', problem_title='T', problem_description='D')
        other = User.objects.create_user('other', 'o@example.com', 'p')
        Report.objects.create(student=other, course_name='C', problem_type='other', problem_title='X', problem_description='D')
        data = self.client.get(f'{API}reports/').json()
        self.assertEqual([r['problem_title'] for r in data['reports']], ['T'])
        self.assertIn(['technical', 'Technical Issue'], data['form']['problem_type_choices'])

    def test_post(self):
        res = self.client.post(f'{API}reports/', {
            'course_name': 'Python', 'problem_type': 'technical', 'problem_title': 'Bug', 'problem_description': 'Broken',
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['messages'], [{'tags': 'success', 'message': 'Aapki report successfully submit ho gayi hai!'}])
        self.assertEqual(Report.objects.get().student, self.user)

    def test_post_invalid(self):
        res = self.client.post(f'{API}reports/', {'course_name': 'Python'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('problem_type', res.json()['errors'])
        self.assertFalse(Report.objects.exists())


class PerformanceApiTests(StudentApiBase):
    def test_no_course(self):
        data = self.client.get(f'{API}performance/').json()
        self.assertIsNone(data['performance'])

    @patch('alvixapp.certificate_service.generate_qr_base64_data_uri', return_value='data:image/png;base64,')
    def test_with_course(self, _qr):
        gc = self.make_course(lessons=2)
        data = self.client.get(f'{API}performance/').json()
        perf = data['performance']
        self.assertEqual(perf['total_days'], 2)
        self.assertEqual(perf['overall_percentage_text'], '0.0')
        self.assertEqual(perf['pass_mark_text'], '35')
        self.assertEqual(perf['first_day_max_score_text'], '50.0')
        self.assertEqual(len(perf['days']), 2)
        self.assertEqual(perf['days'][0]['fmt']['watch_time_pct'], '0')
        self.assertEqual(data['active_course']['display_title'], 'Python Basics')
        self.assertEqual(data['active_course']['id'], gc.id)
        self.assertEqual(data['remaining_lessons'], 2)
        self.assertEqual(data['score_gap_text'], '35.0')
        self.assertFalse(data['certificate']['is_unlocked'])

    @patch('alvixapp.certificate_service.generate_qr_base64_data_uri', return_value='data:image/png;base64,')
    def test_dashboard_matches_performance_record(self, _qr):
        from .models import AssignmentSubmission, QuizSubmission
        self.complete_assessment()
        self.make_course(lessons=1)  # an older enrolment must not be the one summarised
        gc = self.make_course(lessons=2)
        day1, day2 = gc.daily_lessons.order_by('day_number')
        DailyLesson.objects.filter(pk=day1.pk).update(watch_time_seconds=90, is_completed=True)
        AssignmentSubmission.objects.create(user=self.user, lesson=day1, marks=7, score=7, total_marks=10)
        QuizSubmission.objects.create(user=self.user, lesson=day1, score=3, total_questions=5, percentage=60)
        QuizSubmission.objects.create(user=self.user, lesson=day2, score=5, total_questions=5, percentage=100)

        dashboard = self.client.get(f'{API}dashboard/').json()
        perf = self.client.get(f'{API}performance/').json()['performance']
        self.assertEqual(dashboard['active_course']['id'], gc.id)
        # day 1: 50% watch*0.2 + 70% assign*0.4 + 60% quiz*0.4 = 62; day 2: 100% quiz*0.4 = 40 -> 51.0
        self.assertEqual(perf['overall_percentage_text'], '51.0')
        self.assertEqual(dashboard['overall_progress'], 51.0)
        self.assertEqual(dashboard['grade'], perf['grade'])
        self.assertIn('51.0%', dashboard['ai_remarks'])


class SettingsApiTests(StudentApiBase):
    def test_get(self):
        data = self.client.get(f'{API}settings/').json()
        self.assertEqual(data['form'], {'theme': 'Dark', 'email_notifications': True,
                                        'ai_notifications': True, 'public_profile': True})

    def test_post(self):
        res = self.client.post(f'{API}settings/', {'theme': 'Dark', 'email_notifications': 'on'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['messages'][0]['message'], 'Settings updated successfully!')
        self.assertEqual(data['user']['settings']['theme'], 'Dark')
        s = UserSettings.objects.get(user=self.user)
        self.assertEqual(s.theme, 'Dark')
        self.assertTrue(s.email_notifications)
        self.assertFalse(s.ai_notifications)
        self.assertFalse(s.public_profile)

    def test_post_invalid(self):
        res = self.client.post(f'{API}settings/', {'theme': ''})
        self.assertEqual(res.status_code, 400)
        self.assertIn('theme', res.json()['errors'])
        self.assertEqual(res.json()['messages'][0]['message'], 'Please correct the errors below.')

    def test_post_rejects_unknown_theme(self):
        res = self.client.post(f'{API}settings/', {'theme': 'Sepia'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('theme', res.json()['errors'])
