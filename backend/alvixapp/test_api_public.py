"""Tests for /api/v1/public/ (signup + verification, suggested courses, certificate verify)."""

import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from .models import AdminCourse, Certificate, GeneratedCourse, Profile, StudentAssessment

SIGNUP = '/api/v1/public/signup/'
VERIFY = '/api/v1/public/signup/verify/'
SUGGESTED = '/api/v1/public/suggested-courses/'

FORM = {
    'full_name': 'New Student', 'username': 'newstudent', 'email': 'new@example.com',
    'password': 'Sup3r-secret-pw', 'confirm_password': 'Sup3r-secret-pw',
}


def post_json(client, url, data):
    return client.post(url, data, content_type='application/json')


class SignupApiTests(TestCase):
    def test_step1_sends_code_and_stores_only_hash(self):
        res = post_json(self.client, SIGNUP, FORM)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['step'], 'verify')
        self.assertEqual(body['email'], 'new@example.com')
        self.assertIsNone(body['verification_code_debug'])  # DEBUG is False under tests
        self.assertEqual(len(mail.outbox), 1)
        pending = self.client.session['pending_signup_data']
        self.assertNotIn('password', pending)
        self.assertNotIn('Sup3r-secret-pw', str(dict(self.client.session)))
        self.assertFalse(User.objects.filter(username='newstudent').exists())

    @override_settings(DEBUG=True)
    def test_step1_debug_code(self):
        body = post_json(self.client, SIGNUP, FORM).json()
        self.assertEqual(str(body['verification_code_debug']), str(self.client.session['signup_verification_code']))

    def test_step1_errors_keep_saved_data(self):
        res = post_json(self.client, SIGNUP, {**FORM, 'confirm_password': 'other'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error'], 'Passwords do not match.')
        self.assertEqual(res.json()['saved_data'], {'full_name': 'New Student', 'username': 'newstudent', 'email': 'new@example.com'})

        User.objects.create_user('NewStudent', 'x@example.com', 'p')
        self.assertEqual(post_json(self.client, SIGNUP, FORM).json()['error'],
                         'Username is already taken. Please choose another one.')
        self.assertEqual(post_json(self.client, SIGNUP, {**FORM, 'username': 'other', 'email': 'X@example.com'}).json()['error'],
                         'An account with this email already exists.')

    def test_step1_rejects_weak_password(self):
        weak_password = 'alllowercase1'
        res = post_json(self.client, SIGNUP, {
            **FORM,
            'password': weak_password,
            'confirm_password': weak_password,
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('uppercase letter', res.json()['error'])

    def test_step2_wrong_code_stays_on_verify(self):
        post_json(self.client, SIGNUP, FORM)
        res = post_json(self.client, VERIFY, {'verify_code_submit': '1', 'verification_code': '000000x'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), {'ok': False, 'error': 'Invalid verification code. Please try again.',
                                      'step': 'verify', 'email': 'new@example.com'})

    def test_step2_without_session_is_expired(self):
        res = post_json(self.client, VERIFY, {'verify_code_submit': '1', 'verification_code': '123456'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error'], 'Session expired. Please fill the registration form again.')
        self.assertIsNone(res.json()['step'])

    def test_step2_success_creates_user_and_logs_in(self):
        AdminCourse.objects.create(title='Web Development', description='Web development course')
        post_json(self.client, SIGNUP, FORM)
        code = str(self.client.session['signup_verification_code'])
        res = post_json(self.client, VERIFY, {'verify_code_submit': '1', 'verification_code': code})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['redirect'], '/assessment/')
        self.assertTrue(body['user']['is_authenticated'])
        user = User.objects.get(username='newstudent')
        self.assertTrue(user.check_password('Sup3r-secret-pw'))
        self.assertTrue(StudentAssessment.objects.filter(user=user).exists())
        self.assertTrue(self.client.get('/api/v1/auth/me/').json()['is_authenticated'])
        self.assertNotIn('pending_signup_data', self.client.session)

    def test_legacy_verify_otp_page(self):
        self.assertEqual(self.client.get(VERIFY).json(), {'redirect': '/signup/'})
        self.assertEqual(post_json(self.client, VERIFY, {'otp_code': '1'}).json()['redirect'], '/signup/')

        post_json(self.client, SIGNUP, FORM)
        self.assertEqual(self.client.get(VERIFY).json(), {'email': 'new@example.com'})
        bad = post_json(self.client, VERIFY, {'otp_code': 'nope'})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.json()['error'], 'Invalid verification code. Please try again.')
        code = str(self.client.session['signup_verification_code'])
        ok = post_json(self.client, VERIFY, {'otp_code': code})
        self.assertEqual(ok.json()['redirect'], '/assessment/')

    def test_legacy_views_still_work(self):
        res = self.client.post('/signup/', FORM)
        self.assertContains(res, 'Confirm Email Address')
        code = str(self.client.session['signup_verification_code'])
        res = self.client.post('/signup/', {'verify_code_submit': '1', 'verification_code': code})
        self.assertRedirects(res, '/assessment/', fetch_redirect_response=False)


@patch('alvixapp.ppt_service.generate_slide_audio_gtts', return_value=True)
@patch('alvixapp.ppt_service.synthesize_speech', return_value=True)
class SuggestedCoursesApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('stud', 'stud@example.com', 'pw-12345!')
        Profile.objects.filter(user=self.user).update(
            interest_area='Development', goal='Practical', assessment_completed=True,
            expectations='I want to build full stack web apps with clean APIs.')
        self.dev = AdminCourse.objects.create(title='Full-Stack Web Development', course_type='Practical',
                                              description='Practical full-stack web development and coding.')
        self.other = AdminCourse.objects.create(title='Digital Marketing', description='SEO and campaigns.')

    def test_requires_login(self, *_):
        self.assertIn(self.client.get(SUGGESTED).status_code, (401, 403))

    def test_get_payload(self, *_):
        self.client.force_login(self.user)
        body = self.client.get(SUGGESTED).json()
        for key in ('student_name', 'interest_area', 'goal', 'suggested_level', 'ai_reason',
                    'suggested_course', 'other_courses', 'available_levels', 'messages'):
            self.assertIn(key, body)
        self.assertIn('title', body['suggested_course'])
        self.assertIn('course_code', body['suggested_course'])
        self.assertNotIn(body['suggested_course']['id'], [c['id'] for c in body['other_courses']])

    def test_start_suggested(self, *_):
        self.client.force_login(self.user)
        session = self.client.session
        session['recommended_course_id'] = self.dev.id
        session['ai_suggestion_reason'] = 'Because.'
        session['ai_suggested_level'] = 'Intermediate'
        session.save()
        body = post_json(self.client, SUGGESTED, {'action': 'start_suggested', 'level': 'Intermediate'}).json()
        gen = GeneratedCourse.objects.get(user=self.user, admin_course=self.dev)
        self.assertEqual(body['redirect'], f'/course_content/?course_id={gen.id}')
        self.assertEqual(body['messages'][0]['tags'], 'success')
        self.assertIn("Enrolled in 'Full-Stack Web Development' at Intermediate level!", body['messages'][0]['message'])

    def test_pick_other_course(self, *_):
        self.client.force_login(self.user)
        body = post_json(self.client, SUGGESTED, {'action': 'pick_other_course',
                                                  'other_course_id': self.other.id, 'other_level': 'Beginner'}).json()
        self.assertTrue(body['redirect'].startswith('/course_content/?course_id='))
        self.assertEqual(GeneratedCourse.objects.get(user=self.user, admin_course=self.other).level, 'Beginner')

    def test_pick_missing_course_rerenders_with_error(self, *_):
        self.client.force_login(self.user)
        body = post_json(self.client, SUGGESTED, {'action': 'pick_other_course', 'other_course_id': 99999}).json()
        self.assertNotIn('redirect', body)
        self.assertEqual(body['messages'], [{'tags': 'error', 'message': 'Selected course could not be found.'}])
        self.assertIn('suggested_course', body)

    def test_generate_requires_title(self, *_):
        self.client.force_login(self.user)
        body = post_json(self.client, SUGGESTED, {'action': 'generate_new_course', 'custom_course_title': ' '}).json()
        self.assertEqual(body['redirect'], '/suggested_courses/')
        self.assertEqual(body['messages'][0]['message'], 'Please enter a course title to generate.')

    def test_generate_new_course(self, *_):
        self.client.force_login(self.user)
        body = post_json(self.client, SUGGESTED, {'action': 'generate_new_course', 'custom_course_title': 'Kubernetes Ops',
                                                  'custom_level': 'Beginner', 'custom_pace': 'Standard'}).json()
        self.assertTrue(body['redirect'].startswith('/course_content/?course_id='))
        self.assertTrue(GeneratedCourse.objects.filter(user=self.user, admin_course__title='Kubernetes Ops').exists())


class CertificateVerifyApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('grad', 'grad@example.com', 'pw')
        admin_course = AdminCourse.objects.create(title='ML Foundations', description='ML')
        course = GeneratedCourse.objects.create(user=self.user, admin_course=admin_course, level='Beginner', pace='Standard')
        self.cert = Certificate.objects.create(
            certificate_id='ALVIX-CERT-TEST1', user=self.user, course=course, is_unlocked=True, is_valid=True,
            student_name='Grad Student', student_email='grad@example.com', course_name='ML Foundations',
            level='Beginner', start_date=datetime.date(2026, 1, 2), current_date=datetime.date(2026, 1, 9),
            duration_days=7, overall_percentage=92.5, performance_grade='A', ai_review='Great work.')

    def url(self, cid):
        return f'/api/v1/public/certificates/{cid}/verify/'

    def test_valid_is_public(self):
        body = self.client.get(self.url('ALVIX-CERT-TEST1')).json()
        self.assertTrue(body['is_valid'])
        self.assertEqual(body['cert_id'], 'ALVIX-CERT-TEST1')
        self.assertEqual(body['certificate']['overall_percentage'], '92.5')
        self.assertEqual(body['certificate']['start_date'], '2026-01-02')
        self.assertEqual(body['certificate']['ai_review'], 'Great work.')
        self.assertTrue(body['verification_time'])

    def test_invalid(self):
        body = self.client.get(self.url('FAKE-ID-9999')).json()
        self.assertFalse(body['is_valid'])
        self.assertIsNone(body['certificate'])
        Certificate.objects.filter(pk=self.cert.pk).update(is_unlocked=False)
        body = self.client.get(self.url('ALVIX-CERT-TEST1')).json()
        self.assertFalse(body['is_valid'])
        self.assertIsNone(body['certificate'])
