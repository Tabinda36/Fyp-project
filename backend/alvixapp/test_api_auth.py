"""Tests for the session-auth API, permissions helper and fixed backend bugs."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile
from .permissions import is_alvix_admin


class AuthApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('student1', 'student1@example.com', 'Str0ng-pass!')

    def test_csrf_and_me_anonymous(self):
        res = self.client.get('/api/v1/auth/csrf/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('csrftoken', res.cookies)
        me = self.client.get('/api/v1/auth/me/').json()
        self.assertFalse(me['is_authenticated'])

    def test_login_with_email_routes_to_assessment_first(self):
        res = self.client.post('/api/v1/auth/login/', {'email': 'student1@example.com', 'password': 'Str0ng-pass!'},
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['redirect'], '/assessment/')
        me = self.client.get('/api/v1/auth/me/').json()
        self.assertTrue(me['is_authenticated'])
        self.assertEqual(me['email'], 'student1@example.com')
        self.assertTrue(me['profile']['student_id'].startswith('ALVIX-'))

    def test_login_routes_to_dashboard_after_assessment(self):
        Profile.objects.filter(user=self.user).update(assessment_completed=True)
        res = self.client.post('/api/v1/auth/login/', {'email': 'student1@example.com', 'password': 'Str0ng-pass!'},
                               content_type='application/json')
        self.assertEqual(res.json()['redirect'], '/dashboard/')

    def test_login_invalid(self):
        res = self.client.post('/api/v1/auth/login/', {'email': 'student1@example.com', 'password': 'nope'},
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error'], 'Invalid email or password.')

    def test_logout(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post('/api/v1/auth/logout/').status_code, 200)
        self.assertFalse(self.client.get('/api/v1/auth/me/').json()['is_authenticated'])


class AdminPermissionTests(TestCase):
    def test_staff_is_admin(self):
        self.assertTrue(is_alvix_admin(User.objects.create_user('boss', 'b@x.com', 'p', is_staff=True)))

    def test_old_hardcoded_usernames_are_not_admin(self):
        for name in ('admin', 'tabinda', 'taabinda'):
            self.assertFalse(is_alvix_admin(User.objects.create_user(name, f'{name}@x.com', 'p')))

    def test_email_never_grants_admin(self):
        # students can edit their own email, so admin must not depend on it
        self.assertFalse(is_alvix_admin(User.objects.create_user('owner', 'tabindarukhsar36@gmail.com', 'p')))

    def test_grant_admin_command(self):
        from django.core.management import call_command
        u = User.objects.create_user('owner', 'owner@alvix.local', 'p')
        call_command('grant_admin', 'owner@alvix.local', stdout=open(__import__('os').devnull, 'w'))
        u.refresh_from_db()
        self.assertTrue(is_alvix_admin(u))


class SecurityFixTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('stud', 'stud@example.com', 'p')
        self.other = User.objects.create_user('other', 'other@example.com', 'p')
        self.client.force_login(self.user)

    def test_anonymous_login_requires_csrf(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        r = c.post('/api/v1/auth/login/', {'email': 'stud@example.com', 'password': 'p'}, content_type='application/json')
        self.assertEqual(r.status_code, 403)

    def test_profile_rejects_duplicate_and_invalid_email(self):
        for bad in ('other@example.com', 'not-an-email'):
            r = self.client.post('/api/v1/student/profile/', {'full_name': 'S', 'email': bad})
            self.assertEqual(r.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'stud@example.com')

    def test_profile_rejects_non_image_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        evil = SimpleUploadedFile('x.html', b'<script>alert(1)</script>', content_type='text/html')
        r = self.client.post('/api/v1/student/profile/', {'full_name': 'S', 'email': 'stud@example.com', 'profile_picture': evil})
        self.assertEqual(r.status_code, 400)
        fake_png = SimpleUploadedFile('x.png', b'<script>alert(1)</script>', content_type='image/png')
        r = self.client.post('/api/v1/student/profile/', {'full_name': 'S', 'email': 'stud@example.com', 'profile_picture': fake_png})
        self.assertEqual(r.status_code, 400)

    def test_profile_without_email_keeps_email(self):
        r = self.client.post('/api/v1/student/profile/', {'full_name': 'S'})
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'stud@example.com')

    def test_otp_attempts_are_limited(self):
        from django.test import Client
        c = Client()
        c.post('/api/v1/public/signup/', {'full_name': 'N', 'username': 'newbie', 'email': 'n@example.com',
                                          'password': 'Sup3r-secret-pw', 'confirm_password': 'Sup3r-secret-pw'})
        for _ in range(5):
            r = c.post('/api/v1/public/signup/verify/', {'verification_code': '000000'})
        self.assertIn('Too many', r.json()['error'])
        self.assertIsNone(c.session.get('pending_signup_data'))


class FixedBugTests(TestCase):
    def test_profile_requires_login(self):
        res = self.client.get(reverse('profile'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('login'), res['Location'])

    def test_mark_notification_read_requires_login(self):
        res = self.client.post('/notifications/read/1/')
        self.assertEqual(res.status_code, 302)

    def test_signup_session_never_stores_plain_password(self):
        self.client.post(reverse('signup'), {
            'full_name': 'New Student', 'username': 'newstudent', 'email': 'new@example.com',
            'password': 'Sup3r-secret-pw', 'confirm_password': 'Sup3r-secret-pw',
        })
        pending = self.client.session.get('pending_signup_data') or {}
        self.assertNotIn('password', pending)
        self.assertNotIn('Sup3r-secret-pw', str(dict(self.client.session)))
